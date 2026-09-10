import tkinter as tk
from tkinter import messagebox
from itertools import product
import threading

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
    return ones == 3 and zeroes == 3 and not ('111' in binary_str) and not ('000' in binary_str)

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
        # Check if three numbers are not consucutive in a column
        for i in range(4):
            valid = valid and not (get_bit(numbers[i], bit_position)==get_bit(numbers[i+1], bit_position)
                                      ==get_bit(numbers[i+2], bit_position))
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

### The above was from Tango_Solver .py, which is the original code. The below is the GUI code for the same.
#This will create a GUI for the Tango Solver, which will take input from the user and display the output in a text box.


class TangoSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tango Solver GUI")
        self.clear_grid() # Initialize the grid with default values

    def clear_grid(self):
        self.numbers = [11, 13, 19, 21, 22, 25] # Example list of numbers
        self.set_string = []
        self.set_sign_x = []
        self.set_sign_y = []
        self.grid = [[" " for _ in range(11)] for _ in range(11)]
        self.create_widgets()
        self.valid_numbers = [i for i in range(64) if validate_number(i)]

    def create_widgets(self):
        self.instructions = tk.Label(self.root, text="Click to add set_string, set_sign_x, and set_sign_y")
        self.instructions.grid(row=0, column=0, columnspan=11)

        for i in range(11):
            for j in range(11):
                if i % 2 == 0 and j % 2 == 0:
                    button = tk.Button(self.root, background="#FFFFFF", text=self.grid[i][j], command=lambda i=i, j=j: self.toggle10(i, j))
                elif i % 2 == 0 or j % 2 == 0:
                    button = tk.Button(self.root, background="#0FFF00", text=self.grid[i][j], command=lambda i=i, j=j: self.toggle_sign(i, j))
                else:
                    button = tk.Label(self.root, text="X")
                button.grid(row=i+1, column=j, padx=2, pady=1)

        self.solve_button = tk.Button(self.root, text="Solve", command=self.solve)
        self.solve_button.grid(row=12, column=0, columnspan=5)
        self.clear_button = tk.Button(self.root, text="Clear", command=self.clear_grid)
        self.clear_button.grid(row=12, column=6, columnspan=5)
        #now display the full list grid in the text box, which will get refreshed with the above grid.
        self.result_text = tk.Text(self.root, height=20, width=50)
        self.result_text.grid(row=1, column=12, rowspan=11)
        #this is the grid that will be displayed in the text box
        for row in self.grid:
            self.result_text.insert(tk.END, ' '.join(row) + '\n')
        self.solveGrid()
  
  #      self.result_text = tk.Text(self.root, height=20, width=50)
  #      self.result_text.grid(row=13, column=0, columnspan=11)

    def toggle10(self, i, j):
        if self.grid[i][j] == " ":
            self.grid[i][j] = "0"
        elif self.grid[i][j] == "0":
            self.grid[i][j] = "1"
        else:
            self.grid[i][j] = " "
        self.update_grid()

    def toggle_sign(self, i, j):
        if self.grid[i][j] == " ":
            self.grid[i][j] = "+"
        elif self.grid[i][j] == "+":
            self.grid[i][j] = "="
        else:
            self.grid[i][j] = " "
        self.update_grid()

    def update_grid(self):
        #this should delete the grid and recreate it
        self.create_widgets()
        pass
    
    def print_tango_GUI(self, numbers):
        # Print the first line
        self.result_text.insert(tk.END, "5 4 3 2 1 0 -|-X\n")
        self.result_text.insert(tk.END, "-------------|--\n")
        # Print each number in the list with its corresponding line number
        for i in range(len(numbers)):
            self.result_text.insert(tk.END, f"{print_binary_with_spaces(numbers[i])} ")
            self.result_text.insert(tk.END, f"-|-{i} \n")

    def solveGrid(self):
        self.set_string = []
        self.set_sign_x = []
        self.set_sign_y = []
        # First Initialize  the set_string, set_sign_x and set_sign_y
        for j in range(11):
            for i in range(11):
                if self.grid[i][j] == " ":
                    continue
                elif i % 2 == 0 and j % 2 == 0:
                    if self.grid[i][j] == "0":
                        self.set_string.append([0, 5-j//2, (i//2)])
                    elif self.grid[i][j] == "1":
                            self.set_string.append([1, 5-j//2, i//2])
                elif i % 2 == 1 and j % 2 == 0:
                    if self.grid[i][j] == "+":
                        self.set_sign_y.append(['+', (i-1)//2, (i+1)//2, 5-j//2])
                    elif self.grid[i][j] == "=":
                        self.set_sign_y.append(['=', (i-1)//2, (i+1)//2, 5-j//2])
                elif i % 2 == 0 and j % 2 == 1:
                    if self.grid[i][j] == "+":
                        self.set_sign_x.append(['+', 5-(j-1)//2, 5-(j+1)//2, i//2])
                    elif self.grid[i][j] == "=":
                        self.set_sign_x.append(['=', 5-(j-1)//2, 5-(j+1)//2, i//2])   
                else:
                    pass

        self.result_text.insert(tk.END, f"Set String: {self.set_string}\n")
        self.result_text.insert(tk.END, f"Set Sign X: {self.set_sign_x}\n")
        self.result_text.insert(tk.END, f"Set Sign Y: {self.set_sign_y}\n")
        print(self.set_string, end=" ")
        print(self.set_sign_x,self.set_sign_y, end=" ")

    def solve(self):
        self.solveGrid()
        solve_thread = threading.Thread(target=self.solve_tango)
        self.count = 0
        solve_thread.start()

    def solve_tango(self):
        for combination in product(self.valid_numbers, repeat=6):
            self.numbers = list(combination)
            if self.numbers != num_set_string(self.set_string, self.numbers) or self.numbers != num_set_sign_x(self.set_sign_x, self.numbers) or self.numbers != num_set_sign_y(self.set_sign_y, self.numbers):
                continue
            if validate_tango(self.numbers):
                self.count += 1
                result_window = tk.Toplevel(self.root)
                result_window.title(f"Solution {self.count}")
                result_text = tk.Text(result_window, height=20, width=50)
                result_text.pack()
                result_text.insert(tk.END, f"Solution {self.count}:\n")
                result_text.insert(tk.END, f"Numbers: {self.numbers}\n")
                result_text.insert(tk.END, "Tango:\n")
                for i in range(len(self.numbers)):
                    result_text.insert(tk.END, f"{print_binary_with_spaces(self.numbers[i])} -|-{i}\n")
                if self.count == 3:
                    break

if __name__ == "__main__":
    root = tk.Tk(screenName="Tango Solver GUI")
    app = TangoSolverGUI(root)
    root.mainloop()
