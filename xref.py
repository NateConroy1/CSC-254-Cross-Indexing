import datetime
import os
import re
import sys
from subprocess import call

timeRan = str(datetime.datetime.now())

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
# {<pc> : [[<pc>, <op code>, <optional instruction tail>], <last instruction flag>]}
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

with open('objdump.txt', 'r') as objdump_file:
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
                    assembly[pc] = [[pc] + instruction, False]
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

with open('dwarfdump.txt', 'r') as dwarfdump_file:
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
objdump_keys.sort(reverse=False)

# get a list of the dwarfdump keys
dwarfdump_keys = list(pc_source_code_mapping.keys())
# sort the keys in ascending order
dwarfdump_keys.sort(reverse = False)

# declare a variable to hold the next dwarfdump pc value
next_pc = dwarfdump_keys[0]

# dictionary to hold the next lines for each file
# format: { <file path> : <next line> }
read_lines = {}
# dictionary to hold the source code for each file
source_code = {}
# dictionary of function headers
function_headers = {}

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

    file_path = pc_source_code_mapping[pc][0]

    function_header_regex = re.compile(r'((\w)+( )+)+(\w)+( )*\((.)*\)( )*{')

    # if it is the first time we've seen the file
    if file_path not in read_lines:
        # read the file and save the source code
        f = open(file_path, 'r')
        source_code[file_path] = f.readlines()
        read_lines[file_path] = []
        function_headers[file_path] = []
        for line in source_code[file_path]:
            if function_header_regex.search(line):
                function_headers[file_path].append(line)

    # convert list of strings to ints
    line_nums = list(map(int, pc_source_code_mapping[pc][1]))
    # get the minimum line number already added
    line_number = max(line_nums)

    # add the file number that is seen in the dwarfdump entry
    chunk[0].append(source_code[file_path][line_number - 1])

    continue_loop = True

    # if function header is reached
    source_line = source_code[file_path][line_number - 1]
    if source_line in function_headers[file_path]:
        continue_loop = False
        # if it is first function header, continue
        if function_headers[file_path].index(source_line) == 0:
            continue_loop = True

    line_number = line_number - 1

    while continue_loop:

        break_while = False

        # if any previous dwarfdump contains line number, break
        for previous_pc in dwarfdump_keys:
            if previous_pc == pc:
                break
            if str(line_number) in pc_source_code_mapping[previous_pc][1]:
                continue_loop = False
                break_while = True
                break
        if break_while:
            break

        # if first line of file is reached, don't continue
        if line_number == 0:
            continue_loop = False
            break

        # if function header is reached
        source_line = source_code[file_path][line_number - 1]
        if source_line in function_headers[file_path]:
            continue_loop = False
            # if it is first function header, continue
            if function_headers[file_path].index(source_line) == 0:
                continue_loop = True

        chunk[0].append(source_code[file_path][line_number-1])
        line_number = line_number - 1

    # append chunk to program
    program.append(chunk)

# reverse the order of the source code
for i in range(len(program)):
    program[i][0].reverse()

print(program)

##############################
# CREATE CROSS_INDEXING.HTML #
##############################

cross_indexing = open("html/cross_indexing.html","w+")
cross_indexing.write("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>CSC_254 A4</title>
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

control_transfer = ["jmp", "je", "jne", "jz", "jg", "jge", "jl", "jle", "callq"]

# iterate through each section
for i in range(len(program)):
     cross_indexing.write("<tr><td>")

     # make assembly line up with final source line
     if len(program[i][0]) - len(program[i][1]) < 0:
         for k in range(abs(len(program[i][0]) - len(program[i][1]))):
             cross_indexing.write("<br>")

     # start with no indentations
     numIndents = 0
     # write the source code
     for j in range(len(program[i][0])):

         # indent appropriately
         for k in range(numIndents):
             cross_indexing.write("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
         if len(program[i][0][j]) >= 2 and program[i][0][j][-2] == "{":
             numIndents += 1

         cross_indexing.write(program[i][0][j]+"<br>")

     cross_indexing.write("</td><td>")

     # make source line up with final assembly line
     if len(program[i][1]) - len(program[i][0]) < 0:
         for k in range(abs(len(program[i][1]) - len(program[i][0]))):
             cross_indexing.write("<br>")

     # write the assembly code
     for j in range(len(program[i][1])):

         # convert pc to hex and format correctly
         pc = hex(program[i][1][j][0])[2:].lstrip('0')

         # create div for pc
         cross_indexing.write("<div id=\""+pc+"\">")

         # anchor tag for every fixed-address control transfer (branch or subroutine call)
         if program[i][1][j][1] in control_transfer:
             cross_indexing.write("<a href=#"+program[i][1][j][-1]+">")

         # for each line of assembly code
         for k in range(1, len(program[i][1][j])):
             cross_indexing.write(program[i][1][j][k]+" ")

         # if control transfer, close anchor tag
         if program[i][1][j][1] in control_transfer:
             cross_indexing.write("</a>")

         cross_indexing.write("</div>")

     cross_indexing.write("</td></tr>")

cross_indexing.write("</table></body></html>")
cross_indexing.close()

#####################
# CREATE INDEX.HTML #
#####################

path = os.path.dirname(os.path.realpath(__file__))
index = open("html/index.html","w+")
index.write("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Index: CSC_254 A4</title>
            <style type="text/css">

                * {
                    font-family: monospace;
                    line-height: 1.5em;
                }

            </style>
        </head>
        <body>
            <h1>Cross Indexing<h1>
            <h2>CSC_254 Assignment 4</h2>
            <h3>Luka Sherman and Nathan Conroy</h3>
            <h3>University of Rochester Fall 2017</h3>
            <hr><br><br>
            <strong>xref Run Time: </strong>"""+timeRan+"""<br>
            <strong>xref Run Location: </strong>"""+path+ """<br>
            <br><br>
            <a href="cross_indexing.html">Link to Cross Indexing file with source and assembly</a><br>
            <a href="cross_indexing.html#main">Link to "main" location in cross indexing in file</a>
        </body>
    </html>
            """)

index.close()