import numpy as np
from openfermion import QubitOperator
import openfermion as of
import openfermionpyscf as ofpyscf

from cirq import to_json

from orquestra.quantum.evolution import time_evolution
from orquestra.quantum.circuits import Circuit, T, X
from orquestra.integrations.qiskit.conversions import (
    export_to_qiskit,
)
from orquestra.integrations.cirq.conversions import (
    export_to_cirq, import_from_cirq,
)

from icm.icm_converter import icm_circuit

from cirq import X as X_cirq
from cirq import T as T_cirq
from cirq import CNOT as CNOT_cirq
from cirq import H as H_cirq


def estimate_number_of_trotter_steps(time, accuracy):
    # NOTE: this formula might be actually inaccurate
    # This might provide a better one: https://arxiv.org/abs/1912.08854
    # TODO: it should also depend on the norm of the Hamiltonian. Worth thinking about it future.
    return int(np.ceil(time**2 / accuracy))


def generate_h2_jw_qubit_hamiltonian():
    # Set molecule parameters
    geometry = [("H", (0.0, 0.0, 0.0)), ("H", (0.0, 0.0, 0.8))]
    basis = "sto-3g"
    multiplicity = 1
    charge = 0

    # Perform electronic structure calculations and
    # obtain Hamiltonian as an InteractionOperator
    hamiltonian = ofpyscf.generate_molecular_hamiltonian(
        geometry, basis, multiplicity, charge
    )

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


def mock_transpile_clifford_t(circuit):
    new_list = []
    for gate_operation in circuit.operations:
        if gate_operation.gate.name == "RZ":
            new_list.append(T(gate_operation.qubit_indices[0]))
        if gate_operation.gate.name == "RX":
            new_list.append(X(gate_operation.qubit_indices[0]))
        else:
            new_list.append(gate_operation)
    new_circuit = Circuit(new_list)
    return new_circuit




def generate_icm_trotter_circuit(time, precision):
    number_of_qubits = 4
    qubit_hamiltonian = generate_h2_jw_qubit_hamiltonian()
    control_hamiltonian = add_control_qubit_to_qubit_hamiltonian(
        qubit_hamiltonian, number_of_qubits
    )

    # TODO: explain where this comes from
    trotter_error = precision / 10

    ### Prepare unitary circuit
    n_trotter_steps = estimate_number_of_trotter_steps(time, trotter_error)
    trotter_circuit = time_evolution(
        control_hamiltonian, time=time, trotter_order=n_trotter_steps
    )

    ## Prepare algorithm circuit
    circuit = trotter_circuit
    transpiled_circuit = mock_transpile_clifford_t(circuit)

    cirq_circuit = export_to_cirq(transpiled_circuit)

    # # For Athena's testing purposes
    # file_name = f"for_athena"
    # file_name = file_name.replace(".", "_") + ".json"
    # with open(file_name, "w") as f:
    #     f.write(to_json(cirq_circuit))    

    # ICM Compile
    icm_cirq_circuit = icm_circuit(cirq_circuit, [X_cirq, T_cirq, CNOT_cirq, H_cirq,])
    
    # # Convert to qiskit
    # icm_qiskit_circuit = export_to_qiskit(import_from_cirq(icm_cirq_circuit))

    # file_name = f"time_{time}_error_{trotter_error}"
    # file_name = file_name.replace(".", "_") + ".txt"
    # with open(file_name, "w") as f:
    #     f.write(icm_qiskit_circuit.qasm())

    file_name = f"time_{time}_error_{trotter_error}"
    file_name = file_name.replace(".", "_") + ".json"
    with open(file_name, "w") as f:
        f.write(to_json(icm_cirq_circuit))


def main():

    for time in [1]:
        for precision in [1e-1]:
            generate_icm_trotter_circuit(time, precision)


if __name__ == "__main__":
    main()
