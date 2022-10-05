import numpy as np
import random

from cirq import to_json
from cirq import X as X_cirq
from cirq import T as T_cirq
from cirq import CNOT as CNOT_cirq
from cirq import H as H_cirq
from cirq import TOFFOLI as TOFFOLI_cirq
from cirq import LineQubit, Circuit


def generate_circuit_including_toffoli_gates(number_of_qubits, number_of_gates):

    new_list = []

    for gate_id in range(number_of_gates):
        # random_index = random.sample(range(0, 2), 1)
        random_qubit_indices = random.sample(range(0, number_of_qubits), 3)
        # print(random_index)
        if random.choice([True, False]):
            qubit = LineQubit(random_qubit_indices[0])
            new_list.append(H_cirq(qubit))
        else:
            # new_list.append(H_cirq(LineQubit(random_qubit_indices[0])))
            new_list.append(
                TOFFOLI_cirq(
                    LineQubit(random_qubit_indices[0]),
                    LineQubit(random_qubit_indices[1]),
                    LineQubit(random_qubit_indices[2]),
                )
            )

    new_circuit = Circuit(new_list)

    return new_circuit


number_of_qubits = 10
number_of_gates = 40

random_circuit = generate_circuit_including_toffoli_gates(
    number_of_qubits, number_of_gates
)
print(random_circuit)

file_name = (
    f"random_H_Toffoli_circuit_{number_of_qubits}_qubits_{number_of_gates}_gates"
)
file_name = file_name.replace(".", "_") + ".json"
with open(file_name, "w") as f:
    f.write(to_json(random_circuit))
