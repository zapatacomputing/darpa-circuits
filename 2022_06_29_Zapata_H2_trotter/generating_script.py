from matplotlib.pyplot import table
import numpy as np
from openfermion import QubitOperator

from zquantum.core.evolution import time_evolution
from zquantum.core.circuits import Circuit, H
from qeqiskit.conversions import import_from_qiskit, export_to_qiskit


def estimate_number_of_trotter_steps(time, accuracy):
    # NOTE: this formula might be actually inaccurate
    # This might provide a better one: https://arxiv.org/abs/1912.08854
    # TODO: it should also depend on the norm of the Hamiltonian. Worth thinking about it future.
    return int(np.ceil(time ** 2 / accuracy))


def create_hadamard_test_circuit(unitary_circuit: Circuit) -> Circuit:
    circuit = Circuit([H(0)])
    # Build a controlled version of the unitry circuit

    for op in unitary_circuit.operations:
        # TODO: it's a hack exploiting particular Hamiltonian.
        if op.gate.name == "H":
            circuit += op
        else:
            controlled_op = op.gate.controlled(1)
            circuit += controlled_op(0, *[qubit + 1 for qubit in op.qubit_indices])

    circuit += H(0)
    return circuit


def main():

    for time in [1]:
        for precision in [1e-2, 1e-3]:
            ### INPUTS ###
            hamiltonian = QubitOperator("X0") + QubitOperator("Z0")

            trotter_error = precision / 10

            ### Prepare unitary circuit
            n_trotter_steps = estimate_number_of_trotter_steps(time, trotter_error)
            trotter_circuit = time_evolution(
                hamiltonian, time=time, trotter_order=n_trotter_steps
            )

            ## Prepare algorithm circuit
            circuit = create_hadamard_test_circuit(unitary_circuit=trotter_circuit)
            qiskit_circuit = export_to_qiskit(circuit)
            file_name = f"time_{time}_error_{trotter_error}"
            file_name = file_name.replace(".", "_") + ".txt"
            with open(file_name, "w") as f:
                f.write(qiskit_circuit.qasm())


if __name__ == "__main__":
    main()