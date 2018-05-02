# CSC-254-Cross-Indexing
CSC 254 A4

This repository is the ownership of Nate Conroy and Luka Sherman and has been made public for my personal portfolio. It may not be used to violate academic honesty policies.

## Run Instructions
### If developing on CSUG machines:
Copy over the project files<br>
Run `gcc -g3 -o example/primes example/primes.c`<br>
Run `python3 xref.py example/primes`

### If developing locally:
You're going to need to run the code on the CSUG machines first in order to get the proper 'objdump.txt' and 'dwarfdump.txt' files. Follow those instructions first.<br><br>
Copy over 'objdump.txt' and 'dwarfdump.txt' from the CSUG machine and paste them in your local 'CSC-254-Cross-Indexing' directory.<br><br>
**Important: Comment out everything in the section with the comment 'Run external objdump and dwarfdump and save to text file' in xref.py**. This will stop the program from overwriting the 'objdump.txt' and 'dwarfdump.txt' files you just copied over.<br>
```
'''
f = open('objdump.txt', 'w')
call(["objdump", "-d", executable_name], stdout=f)
f.close()

f = open('dwarfdump.txt', 'w')
call(["dwarfdump", executable_name], stdout=f)
f.close()
'''
```
Run `gcc -g3 -o example/primes example/primes.c`<br>
Run `python3 xref.py example/primes`
