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

'''
f = open('objdump.txt', 'w')
call(["objdump", "-d", executable_name], stdout=f)
f.close()

f = open('dwarfdump.txt', 'w')
call(["dwarfdump", executable_name], stdout=f)
f.close()
'''

###################
# Process objdump #
###################

# dictionary of the form:
# {<pc> : [[<op code>, <optional instruction tail>], <last instruction flag>]}
assembly = {}

# example pattern: '0000000000400470 <main>:'
subprogram_head_pattern = re.compile("(\d|a|b|c|d|e|f){16} <.+>:")

# flag for whether the line is within a subprogram body
# set to true after a subprogram head is matched
# set to false after the end of a subprogram body is found
subprogram_body = False

# used to flag an instruction as the last in a subprogram block
# when the newline character is found
previous_pc = -1

with open('objdump2.txt', 'r') as objdump_file:
    for line in objdump_file:

        # if line matches subprogram_head_pattern
        if subprogram_head_pattern.match(line):
            # set flag to True
            subprogram_body = True

        # if the end of a subprogram's body has not yet been found
        elif subprogram_body is True:
            # if the current line is the end of the body, set the flag to False
            if line == '\n':
                subprogram_body = False
                assembly[previous_pc][1] = True
            else:
                # add assembly to dictionary

                # line should have the following format if it is an instruction:
                # '  400490:\t48 83 ec 08          \tsub    $0x8,%rsp\n'
                # but may have this format if after nop, in which case we want to ignore? maybe
                # '  4005cd:\t00 00 00 \n'

                # split line by tabs
                split_by_tabs = re.split('\t', line)

                # extract pc value by eliminating whitespace and colon
                # and convert from hex to integer
                pc = int(re.sub("[ :]", "", split_by_tabs[0]), 16)

                # if there are 2 tabs (1st format in comment above)
                if len(split_by_tabs) == 3:
                    # extract part after second tab
                    instruction = split_by_tabs[2]
                    # split by white space
                    instruction = re.split('\s+', instruction)
                    # now extract just opcode and tail (if there is one)
                    if len(instruction) < 3:
                        instruction = instruction[:1]
                    else:
                        instruction = instruction[:2]

                    # add instruction to dictionary
                    assembly[pc] = [instruction, False]
                    previous_pc = pc

objdump_file.close()

#####################
# Process dwarfdump #
#####################

# dictionary of the form:
# {<pc> : [<file uri>, [<line numbers>], [<tags>]}
pc_source_code_mapping = {}

# every file should have this line
pc_source_table_header = "<pc>        [lno,col] NS BB ET PE EB IS= DI= uri: \"filepath\"\n"

# flag for whether the line is within the table body
# set to true after header is matched
# set to false after the end of the table is found
within_table = False

# string representing the uri of the table line in focus
current_uri = ""
# regex pattern to match uri in string
uri_pattern = " uri: \"(.+)\""

with open('dwarfdump2.txt', 'r') as dwarfdump_file:
    for line in dwarfdump_file:

        # if line matches the header of the table containing pc values and source code line numbers
        if line == pc_source_table_header:
            # set flag to true
            within_table = True

        # if the line is within the table
        elif within_table is True:
            # if the end of the table is found, set flag to False
            if line == '\n':
                within_table = False
            else:
                # process the data and add it to the dictionary

                # extract the pc value, convert from hex to integer
                pc = int(line.split()[0], 0)

                # if the line contains a uri, update current_uri
                uri = re.search(uri_pattern, line)
                if uri:
                    current_uri = uri.group(1)

                tags = []
                # if the line contains extra tags, extract those
                tag_match = re.search("( [A-Z]{2})+", line)
                if tag_match:
                    tags = tag_match.group(0).split()

                # extract just the line and col
                line_col = re.sub(" +", "", re.split('\[|\]', line)[1])
                # extract the line number
                line_number = line_col.split(',')[0]

                # if the key already exists
                if pc in pc_source_code_mapping:
                    # append the line number to the list
                    pc_source_code_mapping[pc][1].append(line_number)
                    # append the tags to the list
                    for tag in tags:
                        if tag not in pc_source_code_mapping[pc][2]:
                            pc_source_code_mapping[pc][2].append(tag)
                else:
                    # add entry to dictionary
                    pc_source_code_mapping[pc] = [current_uri, [line_number], tags]

dwarfdump_file.close()

##################################
# Pair assembly with source code #
##################################

# create list of chunks, where chunks contain list of souce code and list of assembly
# list of the form:
# [ [[<source code lines>], [<assembly instructions>]], ...]
program = []

# get a list of the objdump keys
objdump_keys = list(assembly.keys())
# sort the keys in ascending order
objdump_keys.sort(reverse = False)

# get a list of the dwarfdump keys
dwarfdump_keys = list(pc_source_code_mapping.keys())
# sort the keys in ascending order
dwarfdump_keys.sort(reverse = False)

# declare a variable to hold the next dwarfdump pc value
next_pc = dwarfdump_keys[0]

# declare a dictionary to hold the next lines for each file
# format: { <file path> : <next line> }
next_lines = {}

# ****** EDGE CASES ****** #
# same pc, multiple file numbers in dwarfdump
# ET, add to current not next

# boolean flag used to skip pc
# this is used when we see an ET to skip ahead to the next block
skip_next = False

for pc in dwarfdump_keys:

    # if flag is True, skip this pc
    if skip_next:
        skip_next = False
        continue

    # declare new chunk
    # format: [[<source code lines>], [<assembly instructions>]]
    chunk = [[], []]

    # add all assembly

    dd_pc_index = dwarfdump_keys.index(pc)
    # if the current dwarfdump instruction is the last, just add it
    if dd_pc_index == len(dwarfdump_keys) - 1:
        chunk[1].append(assembly[next_pc][0])
    else:
        # while the next pc in objdump is not the next pc in dwarfdump
        # add the instruction to the block and move on to the next pc
        while next_pc != dwarfdump_keys[dd_pc_index + 1]:
            chunk[1].append(assembly[next_pc][0])
            next_pc_index = objdump_keys.index(next_pc)
            next_pc = objdump_keys[next_pc_index + 1]
        # if the next_pc has the tag ET
        if "ET" in pc_source_code_mapping[next_pc][2]:
            # while the instruction is not the last in a subprogram
            # add the instruction and move to the next pc
            while assembly[next_pc][1] is False:
                chunk[1].append(assembly[next_pc][0])
                next_pc_index = objdump_keys.index(next_pc)
                next_pc = objdump_keys[next_pc_index + 1]
            chunk[1].append(assembly[next_pc][0])
            if dd_pc_index + 2 != len(dwarfdump_keys):
                next_pc = dwarfdump_keys[dd_pc_index + 2]
            # skip the next pc
            skip_next = True

    # add all source code



    # append chunk to program
    program.append(chunk)

print(program)



f= open("assembly.html","w+")
f.write("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>CSC254 A4 (Sherman+Conroy)</title>
            <style type="text/css">

                * {
                    font-family: monospace;
                    line-height: 1.5em;
                }

                table {
                    width: 100%;
                }

                td
                {
                    padding: 8px;
                    border-bottom: 2px solid black;
                    vertical-align: bottom;
                    width: 50%;
                }

                th
                {
                    border: 1px solid black;
                }

                .grey {
                    color: #888
                }

            </style>
        </head>
        <body>
            <table>""")

# iterate through each section
for i in range(len(program)):
     f.write("<tr><td>")

     # write the source code
     for j in range(len(program[i][1])):

         # for each line of source code
         for k in range(len(program[i][1][j])):
             f.write(program[i][1][j][k]+" ")

         f.write("<br>")

     f.write("</td><td>")

     # write the assembly code
     for j in range(len(program[i][1])):

         #for each line of assembly code
         for k in range(len(program[i][1][j])):
             f.write(program[i][1][j][k]+" ")

         f.write("<br>")

     f.write("</td></tr>")

f.write("</table></body></html>")
f.close()
