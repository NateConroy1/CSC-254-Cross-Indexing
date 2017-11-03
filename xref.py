import sys
from subprocess import call

if(len(sys.argv) != 2):
    print("Error. Expected 2 arguments, found " + str(len(sys.argv)) + ".")
    exit(1)

executable = sys.argv[1]

# run objdump and save to text file
f = open('objdump.txt', 'w')
call(["objdump", "-d", executable], stdout=f)
f.close()

# run dwarfdump and save to text file
f = open('dwarfdump.txt', 'w')
call(["dwarfdump", executable], stdout=f)
f.close()
