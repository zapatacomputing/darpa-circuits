# darpa-circuits

This repository has been created to store circuit instances that would be useful for DARPA TA2 projects.

While adding new circuits please follow the procedure below:

- Open terminal and ensure that you have git installed. 
- Navigate to the directory you want to work in.
- Run `git clone https://github.com/zapatacomputing/darpa-circuits.git`
- Inside the newly created darpa-circuits folder, create a new directory with the date (YYYY_MM_DD), name and short description, e.g.: 2022_04_11_Zapata_simple_trotter
- Copy circuit_description_template.md from the main directory into yours and fill it in with the details.
- All the circuits should be stored in QASM format
- If there's any additional files that you want to add (e.g. code for generation or loading the circuits), feel free to add it. 
- In terminal, run the following lines of code
  - `git add .`
  - `git commit -m "added <Name of new directory you just made>"`
  - `git push origin`
- If you have any issues don't hesitate to contact the Zapata team

If you want to add new people into this repository please ask either Michał Stęchły (michal.stechly@zapatacomputing.com) or Peter Johnson (peter@zapatacomputing.com)

