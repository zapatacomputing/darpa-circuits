# Darpa circuits

## Introduction

One of the problems we're trying to solve at [DARPAs Quantum Benchmarking program](https://www.darpa.mil/program/quantum-benchmarking) is compilation and resource estimation for fault tolerant architectures. 

The goal of this repository is to store quantum circuits which can be later used by various teams participating in the project for analyzing how their compilation methods work.

If you're not involved in this DARPA program in some form, we doubt this repository will be of any interest to you right now, as we're still in the early stage of research. Hopefully, in future we'll be able to transform it into a more robust library of interesting circuits that community can use for projects relating to compilation and resource estimation.

## Instructions for adding new circuits.
While adding new circuits please follow the procedure below:

- Open terminal and ensure that you have git installed. 
- Navigate to the directory you want to work in.
- Run `git clone https://github.com/zapatacomputing/darpa-circuits.git`
- Inside the newly created darpa-circuits folder, create a new directory with the date (YYYY_MM_DD), name and short description, e.g.: 2022_04_11_Zapata_simple_trotter
- Copy circuit_description_template.md from the main directory into yours and fill it in with the details.
- All the circuits should be stored in QASM format
- If there's any additional files that you want to add (e.g. code for generation or loading the circuits), feel free to add it. 
- In terminal, run:
  - `git add .`
  - `git commit -m "added <Name of new directory you just made>"`
  - `git push origin`
- If you have any issues don't hesitate to contact the Zapata team

If you want to add new people into this repository please ask either Michał Stęchły (michal.stechly@zapatacomputing.com) or Peter Johnson (peter@zapatacomputing.com)

