import pickle
import numpy as np
from openfermion import QubitOperator
import openfermion as of
from openfermionpyscf import generate_molecular_hamiltonian
import warnings

import time as time_lib
import subprocess
import re

from cirq import to_json

from orquestra.quantum.evolution import time_evolution
from orquestra.quantum.circuits import Circuit, T, X, S, H, I
from orquestra.integrations.cirq.conversions import (
    export_to_cirq,
    import_from_cirq,
    from_openfermion
)

# from icm.icm_converter import icm_circuit

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


def generate_h_chain_jw_qubit_hamiltonian(basis, system_size, grid_spacing=0.8):
    # Set molecule parameters
    grid = [grid_spacing * site for site in range(system_size)]
    geometry = [("H", (0.0, 0.0, grid_location)) for grid_location in grid]
    multiplicity = 2
    charge = 0

    # Perform electronic structure calculations and
    # obtain Hamiltonian as an InteractionOperator
    hamiltonian = generate_molecular_hamiltonian(geometry, basis, multiplicity, charge)

    # Convert to a FermionOperator
    hamiltonian_ferm_op = of.get_fermion_operator(hamiltonian)

    # Map to QubitOperator using the JWT
    hamiltonian_jw = of.jordan_wigner(hamiltonian_ferm_op)

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
        elif char == "I":
            new_list.append(I(gate_operation.qubit_indices[0]))
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
            if np.abs(angle) < synthesis_accuracy:
                warnings.warn("Angle smaller than synthesis accuracym returning identity", UserWarning)
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


def generate_h_chain_clifford_T_qpe_circuit(
    time,
    precision,
    system_size,
    synthesis_accuracy=0.000001,
    grid_spacing=0.8,
    basis_set="sto3g",
):

    qubit_hamiltonian = generate_h_chain_jw_qubit_hamiltonian(
        basis_set,
        system_size,
        grid_spacing,
    )

    number_of_qubits = of.utils.count_qubits(qubit_hamiltonian)

    control_hamiltonian = add_control_qubit_to_qubit_hamiltonian(
        qubit_hamiltonian, number_of_qubits
    )

    # TODO: explain where this comes from
    trotter_error = precision
    # trotter_error = precision / 10

    ### Prepare unitary circuit
    n_trotter_steps = estimate_number_of_trotter_steps(time, trotter_error)

    trotter_circuit = time_evolution(
        from_openfermion(control_hamiltonian), time=time, trotter_order=n_trotter_steps
    )

    ## Prepare algorithm circuit
    circuit = trotter_circuit
    transpiled_circuit = transpile_clifford_t(circuit, synthesis_accuracy)

    cirq_circuit = export_to_cirq(transpiled_circuit)

    file_name = f"hydrogen_chain_{system_size}_sites_{basis_set}_time_{time}_error_{trotter_error}"
    file_name = file_name.replace(".", "_") + ".json"
    with open(file_name, "w") as f:
        f.write(to_json(cirq_circuit))


def main():
    synthesis_accuracy = 1e-5
    for time in [1]:
        for precision in [1e-1]:
            generate_h_chain_clifford_T_qpe_circuit(
                time,
                precision,
                1,
                synthesis_accuracy,
                grid_spacing=0.8,
            )


if __name__ == "__main__":
    main()
