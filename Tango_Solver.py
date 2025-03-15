from itertools import product

def print_binary_with_spaces(number):
    # Convert the number to a 6-bit binary string
    binary_str = format(number, '06b')    
    # Join the binary digits with spaces
    spaced_binary_str = ' '.join(binary_str)
    # return the result
    return spaced_binary_str

def print_tango(numbers):
    # Print the first line
    print("5 4 3 2 1 0 -|-X")
    print("-------------|--")
    # Print each number in the list with its corresponding line number
    for i in range(len(numbers)):
        print(print_binary_with_spaces(numbers[i]), end=" ")
        print(f"-|-{i} ")

def validate_number(number):
    ones = 0
    # Convert the number to a 6-bit binary string
    binary_str = format(number, '06b')
    # Count the number of ones and zeroes
    ones = binary_str.count('1')
    zeroes = binary_str.count('0')
    # Check if there are exactly 3 ones and 3 zeroes
    # Also check if the 1s are not consucutive
    return ones == 3 and zeroes == 3 and not ('111' in binary_str)

#Create a Validate_Tango function to check whether 
# each number when translated to binary, has 3 ones and 3 zeroes or not
def validate_tango(numbers):
    valid = True
    # Column wise checking
    for bit_position in range(6):
        ones = 0
        for number in numbers:
            # Check the bit at the current position
            ones += get_bit(number, bit_position)
        # Check if there are exactly 3 ones and 3 zeroes in this column
        valid = valid and ones == 3 
        if not valid:
            break
     # Column wise checking
    for bit_position in range(6):
        # Check if three 1s are not consucutive in a column
        for i in range(4):
            valid = valid and not (get_bit(numbers[i], bit_position)==get_bit(numbers[i+1], bit_position)
                                      ==get_bit(numbers[i+2], bit_position)==1)
    # Row wise checking now
    for number in numbers:
        valid = valid and validate_number(number)
        if not valid:
            break
    return valid

def get_bit(number, position):
    return (number >> position) & 1

def set_bit(number, position, bit):
    mask = 1 << position
    number = number & ~mask  # for setting bit as 0
    number = number | (bit << position) # for setting bit as 1
    return number

#This function will get the set_string which will be a list of lists [bit, positionx, positiony] 
#This will continue asking the user for input til the user enters '1' for Do you want to enter?
def get_setstring_pos():
    set_string = []
    if int(input("Do you want to enter set_string as a list ?(0 for No, 1 for Yes)?")) == 1:
        set_string = input("Enter the set_string as a list of lists: ")
        return set_string
    else:
        while int(input("Do you want to enter set_bits(0 for No, 1 for Yes)?")) == 1:
            print("Enter the bit position and the number position (x, y) where you want to set the bit")
            bit = int(input("Enter the bit (0 or 1): "))
            positionx = int(input("Enter the position x (0 to 5): "))
            positiony = int(input("Enter the position y (0 to 5): "))
            if positionx < 0 or positionx > 5 or positiony < 0 or positiony > 5 or bit < 0 or bit > 1:
                print("Invalid input. Please enter again")
                continue
            set_string.append([bit, positionx, positiony])
    return set_string

#get_sign_x function will get the set_sign_x which will be a list of lists [<eq or ne>, positionx1, positionx2]
#This will continue asking the user for input til the user enters '1' for Do you want to enter?
def get_sign_x():
    set_sign_x = []
    if int(input("Do you want to enter set_sign_x as a list ?(0 for No, 1 for Yes)?")) == 1:
        set_sign_x = input("Enter the set_sign_x as a list of lists: ")
        return set_sign_x
    else:
        while int(input("Do you want to enter set_sign_x(0 for No, 1 for Yes)?")) == 1:
            print("Enter the sign and the number position (x1, x2) where you want to set the sign")
            sign = input("Enter the sign (= or +): ")
            positionx1 = int(input("Enter the position x1 (0 to 5): "))
            positionx2 = int(input("Enter the position x2 (0 to 5): "))
            positiony = int(input("Enter the position y (0 to 5): "))
            if positionx1 == positionx2 or positionx1 < 0 or positionx1 > 5 or positionx2 < 0 or positionx2 > 5 or sign not in ['=', '+']:
                print("Invalid input. Please enter again")
                continue
            if positionx1<positionx2:
                set_sign_x.append([sign, positionx1, positionx2, positiony])
            else:
                set_sign_x.append([sign, positionx2, positionx1, positiony])
    return set_sign_x

def get_sign_y():
    set_sign_y = []
    if int(input("Do you want to enter set_sign_y as a list ?(0 for No, 1 for Yes)?")) == 1:
        set_sign_y = input("Enter the set_sign_y as a list of lists: ")
        return set_sign_y
    else:
        while int(input("Do you want to enter set_sign_y(0 for No, 1 for Yes)?")) == 1:
            print("Enter the sign and the number position (y1, y2) where you want to set the sign")
            sign = input("Enter the sign (= or +): ")
            positiony1 = int(input("Enter the position y1 (0 to 5): "))
            positiony2 = int(input("Enter the position y2 (0 to 5): "))
            positionx = int(input("Enter the position x (0 to 5): "))
            if positiony1 == positiony2 or positiony1 < 0 or positiony1 > 5 or positiony2 < 0 or positiony2 > 5 or sign not in ['=', '+']:
                print("Invalid input. Please enter again")
                continue
            if positiony1<positiony2:
                set_sign_y.append([sign, positiony1, positiony2, positionx])
            else:
                set_sign_y.append([sign, positiony2, positiony1, positionx])
    return set_sign_y

def num_set_string(set_string, numbers):
    for bit, positionx, positiony in set_string:
        numbers[positiony] = set_bit(numbers[positiony], positionx, bit)
    return numbers

def num_set_sign_x(set_sign_x, numbers):
    for sign, position1, position2, position in set_sign_x:
        if sign == '=':
            numbers[position]=set_bit(numbers[position], position2, get_bit(numbers[position], position1) )
        elif sign == '+':
            numbers[position]=set_bit(numbers[position], position2, not get_bit(numbers[position], position1) )
    return numbers

def num_set_sign_y(set_sign_y, numbers):
    for sign, position1, position2, position in set_sign_y:
        if sign == '=':
            numbers[position2]=set_bit(numbers[position2], position, get_bit(numbers[position1], position))
        elif sign == '+':
            numbers[position2]=set_bit(numbers[position2], position, not get_bit(numbers[position1], position) )
    return numbers

# Create a list of 6 numbers (0 to 63)
numbers = [11, 13, 19, 21, 22, 25]
set_string = []
set_sign_x = []
set_sign_y = []
valid_numbers = [] #[7, 11, 13, 14, 19, 21, 22, 25, 26, 28, 35, 37, 38, 41, 42, 44, 49, 50, 52, 56]
#                   [11, 13, 19, 21, 22, 25, 26, 35, 37, 38, 41, 42, 44, 49, 50, 52]
for i in range(64):
    if validate_number(i):
        valid_numbers.append(i)

print("The Valid Numbers could be", valid_numbers)
print_tango(numbers)
# Get the set string from the user
set_string = [[1, 1, 0], [0, 3, 0], [1, 5, 0], [1, 1, 2], [0, 4, 3], [1, 0, 5], [1, 2, 5], [0, 4, 5]]
#get_setstring_pos()
#[[0, 2, 0], [1, 3, 0], [0, 1, 1], [0, 4, 1], [1, 1, 2], [1, 4, 2], [0, 2, 4], [0, 3, 4]] #
set_sign_x = [['+',3,4,1], ['+',4,5,1], ['+',0,1,4], ['+',1,2,4]]
#get_sign_x() 
#[['+', 3, 4, 3], ['=', 1, 2, 3]] #
set_sign_y = [['=', 0, 1, 0], ['+', 1, 2, 0], ['+', 3, 4, 5], ['+', 4, 5, 5]] 
#get_sign_y() 
#[['+', 4, 5, 4], ['=', 4, 5, 1]] #
# Iterate through all possible combinations of 6 numbers from 0 to 63
#for combination in product(range(64), repeat=6):
count=0
for combination in product(valid_numbers, repeat=6):
    numbers = list(combination)
    if numbers != num_set_string(set_string, numbers) or numbers != num_set_sign_x(set_sign_x, numbers) or numbers != num_set_sign_y(set_sign_y, numbers):
        continue
    if validate_tango(numbers):
        count+=1
        print(count,set_sign_x,set_sign_y, end=" ")
        print(set_string, end=" ")
        print(numbers)
        print_tango(numbers)
        #break off if 3 solutions are found
        if count == 3:
            break
