import pickle
import numpy as np
from openfermion import QubitOperator
import openfermion as of
import openfermionpyscf as ofpyscf

import time as time_lib
import subprocess
import re

from cirq import to_json

from orquestra.quantum.evolution import time_evolution
from orquestra.quantum.circuits import Circuit, T, X, S, H
from orquestra.integrations.qiskit.conversions import (
    export_to_qiskit,
)
from orquestra.integrations.cirq.conversions import (
    export_to_cirq,
    import_from_cirq,
)

from icm.icm_converter import icm_circuit

from cirq import X as X_cirq
from cirq import T as T_cirq
from cirq import CNOT as CNOT_cirq
from cirq import H as H_cirq


# TODO: add caching option
# CACHED_GRIDSYNTH_RESULTS = {}


def estimate_number_of_trotter_steps(time, accuracy):
    # NOTE: this formula might be actually inaccurate
    # This might provide a better one: https://arxiv.org/abs/1912.08854
    # TODO: it should also depend on the norm of the Hamiltonian. Worth thinking about it future.
    return int(np.ceil(time**2 / accuracy))


def generate_fermi_hubbard_jw_qubit_hamiltonian(
    x_dimension,
    y_dimension,
    tunneling,
    coulomb,
    chemical_potential=0.0,
    spinless=False,
):

    hubbard_model = of.fermi_hubbard(
        x_dimension,
        y_dimension,
        tunneling,
        coulomb,
        chemical_potential,
        spinless,
    )

    # Map to QubitOperator using the JWT
    hamiltonian_jw = of.jordan_wigner(hubbard_model)

    return hamiltonian_jw


def add_control_qubit_to_qubit_hamiltonian(qubit_hamiltonian, number_of_qubits):
    # Ancilla qubit is set to be last qubit
    # Create three terms, where we've ignored the identity term
    # Positive 1/2 of Z on control qubit
    ancilla_Z = 0.5 * QubitOperator(f"Z{number_of_qubits}")
    # Positive 1/2 of I on control qubit and Hamiltonian on system
    system_hamiltonian = 0.5 * qubit_hamiltonian
    # Negative 1/2 of Z on control qubit and Hamiltonian on system
    coupling_hamiltonian = qubit_hamiltonian * ancilla_Z
    control_hamiltonian = ancilla_Z + system_hamiltonian + coupling_hamiltonian
    # Make Hamiltonian coefficients real
    control_hamiltonian.compress()
    return control_hamiltonian


def parse_gate_sequence_str(gate_sequence_str, gate_operation):

    # Remove phase gates from gate sequence
    phase_free_gate_sequence_str = re.sub("W", "", gate_sequence_str.strip("\n"))

    # Reverse gate order (note from gridsynth docs: "Operators are shown in matrix
    # order, not circuit order. This means they are meant to be applied from
    # right to left."
    ordered_phase_free_gate_sequence_str = phase_free_gate_sequence_str[::-1]
    new_list = []

    for char in ordered_phase_free_gate_sequence_str:
        if char == "S":
            new_list.append(S(gate_operation.qubit_indices[0]))
        elif char == "H":
            new_list.append(H(gate_operation.qubit_indices[0]))
        elif char == "T":
            new_list.append(T(gate_operation.qubit_indices[0]))
        elif char == "X":
            new_list.append(X(gate_operation.qubit_indices[0]))
        else:
            raise Exception(f"{char} cannot be converted to a gate operation.")

    new_circuit = Circuit(new_list)

    return new_circuit


def mock_transpile_clifford_t(circuit):
    new_list = []
    for gate_operation in circuit.operations:
        if gate_operation.gate.name == "RZ":
            new_list.append(T(gate_operation.qubit_indices[0]))
        elif gate_operation.gate.name == "RX":
            new_list.append(X(gate_operation.qubit_indices[0]))
        else:
            new_list.append(gate_operation)
    new_circuit = Circuit(new_list)
    return new_circuit


def transpile_clifford_t(circuit, synthesis_accuracy):
    new_list = []
    for gate_operation in circuit.operations:
        if gate_operation.gate.name == "RZ":
            # new_list.append(T(gate_operation.qubit_indices[0]))
            angle = gate_operation.gate.params[0]
            # result = subprocess.run(["./gridsynth", str(angle)])
            result = subprocess.run(
                ["./gridsynth", str(angle), "-e", str(synthesis_accuracy)],
                capture_output=True,
                text=True,
            )
            gate_sequence_str = result.stdout
            gates_from_gridsynth = parse_gate_sequence_str(
                gate_sequence_str, gate_operation
            )
            new_list += gates_from_gridsynth.operations
            # new_list.append(*gates_from_gridsynth.operations)
            # T(gate_operation.qubit_indices[0])
        elif gate_operation.gate.name == "RX":
            new_list.append(X(gate_operation.qubit_indices[0]))
        else:
            new_list.append(gate_operation)
    # breakpoint()
    new_circuit = Circuit(new_list)
    return new_circuit


# TODO: add caching option
# def transpile_clifford_t_with_cache(circuit):
#     new_list = []
#     for gate_operation in circuit.operations:
#         if gate_operation.gate.name == "RZ":
#             # new_list.append(T(gate_operation.qubit_indices[0]))
#             angle = gate_operation.gate.params[0]
#             if angle in CACHED_GRIDSYNTH_RESULTS.keys():
#                 gates_from_gridsynth = CACHED_GRIDSYNTH_RESULTS[angle]
#             else:
#                 result = subprocess.run(["./gridsynth", str(angle)])
#                 gate_sequence_str = result.stdout
#                 gates_from_gridsynth = parse_gate_sequence_str(gate_sequence_str, gate_operation)
#                 CACHED_GRIDSYNTH_RESULTS[angle] = gates_from_gridsynth
#             breakpoint()
#             new_list.append(gates_from_gridsynth)
#             # T(gate_operation.qubit_indices[0])
#         elif gate_operation.gate.name == "RX":
#             new_list.append(X(gate_operation.qubit_indices[0]))
#         else:
#             new_list.append(gate_operation)
#     new_circuit = Circuit(new_list)
#     return new_circuit


def generate_icm_trotter_circuit(
    time,
    precision,
    synthesis_accuracy,
    x_dimension,
    y_dimension,
    tunneling,
    coulomb,
    chemical_potential=0.0,
    spinless=False,
):

    number_of_qubits = x_dimension * y_dimension * (2 ** (1 - spinless))

    qubit_hamiltonian = generate_fermi_hubbard_jw_qubit_hamiltonian(
        x_dimension,
        y_dimension,
        tunneling,
        coulomb,
        chemical_potential,
        spinless,
    )

    control_hamiltonian = add_control_qubit_to_qubit_hamiltonian(
        qubit_hamiltonian, number_of_qubits
    )

    # TODO: explain where this comes from
    trotter_error = precision
    # trotter_error = precision / 10

    ### Prepare unitary circuit
    n_trotter_steps = estimate_number_of_trotter_steps(time, trotter_error)
    trotter_circuit = time_evolution(
        control_hamiltonian, time=time, trotter_order=n_trotter_steps
    )

    ## Prepare algorithm circuit
    circuit = trotter_circuit
    transpiled_circuit = transpile_clifford_t(circuit, synthesis_accuracy)

    cirq_circuit = export_to_cirq(transpiled_circuit)

    # # For Athena's testing purposes
    # file_name = f"for_athena"
    # file_name = file_name.replace(".", "_") + ".json"
    # with open(file_name, "w") as f:
    #     f.write(to_json(cirq_circuit))

    # ICM Compile
    icm_cirq_circuit = icm_circuit(
        cirq_circuit,
        [
            X_cirq,
            T_cirq,
            CNOT_cirq,
            H_cirq,
        ],
    )

    # # Convert to qiskit
    # icm_qiskit_circuit = export_to_qiskit(import_from_cirq(icm_cirq_circuit))

    # file_name = f"time_{time}_error_{trotter_error}"
    # file_name = file_name.replace(".", "_") + ".txt"
    # with open(file_name, "w") as f:
    #     f.write(icm_qiskit_circuit.qasm())

    # Pickle ICM circuit
    # with open("circuit.pickle", "wb") as f:
    #     pickle.dump(icm_cirq_circuit, f)

    file_name = f"time_{time}_error_{trotter_error}"
    file_name = file_name.replace(".", "_") + ".json"
    with open(file_name, "w") as f:
        f.write(to_json(icm_cirq_circuit))


def main():
    synthesis_accuracy = 1e-2
    for time in [1]:
        for precision in [1e-1]:
            generate_icm_trotter_circuit(
                time,
                precision,
                synthesis_accuracy,
                1,
                1,
                1.0,
                4.0,
                chemical_potential=0.5,
                spinless=True,
            )


if __name__ == "__main__":
    main()
