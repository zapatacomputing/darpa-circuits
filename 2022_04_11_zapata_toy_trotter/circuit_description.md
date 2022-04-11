# Toy Trotter circuits

## Description

These circuits are toy models that we used for some early prototyping. Their main use was to have some quick and dirty circuit samples that we could work on.

We have created them by performing Hadamard test on a simple Hamiltonian.

Number of trotter steps was defined by the target trotter error that we wanted to achieve.

## Contact info

Michał Stęchły, Zapata Computing
michal.stechly@zapatacomputing.com

## Files description

- `generating_script.py` - Python script used to generate the circuit.
- `requirements.txt` – file with all the transient dependencies used for generating the circuits
- `time_<T>_error_<E>.txt` – circuits files are in this format, where T represents time, and E target error.

## Software

- I have used [`z-quantum-core`](https://github.com/zapatacomputing/z-quantum-core) v0.17.0 (to generate the circuits) and [`qe-qiskit`](https://github.com/zapatacomputing/qe-qiskit) v0.7.0 (to export them).
- Other transient dependencies are defined in `requirements.txt`. 
- I used Python 3.7.12.

