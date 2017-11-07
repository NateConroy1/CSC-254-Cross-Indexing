import sys
import re
from subprocess import call

##############################
# Get command line arguments #
##############################

if(len(sys.argv) != 2):
    print("Error. Expected 2 arguments, found " + str(len(sys.argv)) + ".")
    exit(1)

executable_name = sys.argv[1]

######################################
# Run external objdump and dwarfdump #
# and save to text file              #
######################################

f = open('objdump.txt', 'w')
call(["objdump", "-d", executable_name], stdout=f)
f.close()

f = open('dwarfdump.txt', 'w')
call(["dwarfdump", executable_name], stdout=f)
f.close()

###################
# Process objdump #
###################

# dictionary of the form:
# {<subprogram_name> : [[<op_code>, <optional_instruction_tail>], ...]}
subprogram_asm = {}

# example pattern: '0000000000400470 <main>:'
subprogram_head_pattern = re.compile("(\d|a|b|c|d|e|f){16} <.+>:")

# flag for whether the line is within a subprogram body
# set to true after a subprogram head is matched
# set to false after the end of a subprogram body is found
subprogram_body = False
# name of the subprogram being read
subprogram_name = ""

with open('objdump.txt', 'r') as objdump_file:
    for line in objdump_file:
        
        # if line matches subprogram_head_pattern
        if subprogram_head_pattern.match(line):
            # extract the function name by splitting by the '<' and '>'
            subprogram_name = re.split('<|>', line)[1]
            subprogram_asm[subprogram_name] = []
            # set flag to True
            subprogram_body = True
            
        # if the end of a subprogram's body has not yet been found
        elif subprogram_body is True:
            # if the current line is the end of the body, set the flag to False
            if line == '\n':
                subprogram_body = False
            else:
                # add assembly to dictionary

                # line should have the following format if it is an instruction:
                # '  400490:\t48 83 ec 08          \tsub    $0x8,%rsp\n'
                # but may have this format if after nop, in which case we want to ignore? maybe
                # '  4005cd:\t00 00 00 \n'

                # split line by tabs
                split_by_tabs = re.split('\t', line)
                # if there are 2 tabs (1st format above)
                if len(split_by_tabs) == 3:
                    # extract part after second tab
                    instruction = split_by_tabs[2]
                    instruction = re.split('\s+', instruction)
                    # now extract just opcode and tail (if there is one)
                    if len(instruction) < 3:
                        instruction = instruction[:1]
                    else:
                        instruction = instruction[:2]
                    # add instruction to dictionary
                    subprogram_asm[subprogram_name].append(instruction)
                    
print(subprogram_asm)                    
