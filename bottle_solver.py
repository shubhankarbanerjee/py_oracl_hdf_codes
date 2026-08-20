import tkinter as tk
from tkinter import messagebox

#I want an Object oriented code to solve the bottle problem, which is a game 
#This will contain total Bottles n (default value 6);  and m (default 2) empty bottles
#Each bottle will have capacity of x (default 4) parts; total number of colors used will be y (default 5)
#Color names will be among Net_Color = ['lr', 'lg', 'lb', 'lo', 'lv','dr', 'dg', 'db', 'do', 'dv']
#(light red, light green, light blue, light orange, light violet, dark red, dark green, dark blue, dark orange, dark violet)
#The variables will be entered through the GUI form, using input boxes.
#The form will also have n-m input boxes to enter the colors of the bottles, 
# which will be a list of colors used in the bottle like [color1, color2, color3, color4]
#The form will have two buttons - one to reset the game, and one to solve the game.

#The class game will have the list of variables of type bottles [Bottle1, Bottle2, Bottle3, Bottle4, Bottle5, Bottle6] 
# and the list of other variables used in the game. 
# It will have a method to check if the game is solved by checking if there is no bottle which is not is_locked or is_empty

# The button solve will start solving the game, and will return the solution in a list of steps to be taken to solve the game.
#The solution will be displayed in a new GUI messagebox, along with the number of steps, like:
# It took 4 steps :
# Step 1: Pour(Bottle1, Bottle2), 
# Step 2: Pour(Bottle3, Bottle4), ...

#The class Bottle will have method top color to return the top color of the bottle, 
#  method is_empty to check if the bottle is empty; is_locked() to check if the bottle is locked,
# a bottle will be locked if it is full and it has all parts of one and same color; 
# it will have a list of colors used in the bottle liek [color1, color2, color3, color4]; max x colors
# and method is_full to check if the bottle is full, by checking variable num_parts of the bottle.
#The class Bottle will have method pour to pour the color from one bottle to another 
#This pour will be success (return true) only if the source bottle is not empty, the destination bottle is not is_full,
# and if the destination bottle not is_empty - 
# then the top color of the source bottle is same as the top color of the destination bottle
#The pour method if success, needs to change both bottle(s) the source bottle's num_parts will be reduced by 1,
#  and the destination bottle's num_parts will be increased by 1; the top color of the source bottle will be removed, 
# and the next color will now be the top color of the source bottle. The num_parts of the destination bottle will be added by 1.

class Bottle:
    def __init__(self, capacity=4, colors=[]):
        self.capacity = capacity  # Maximum Number of parts in the bottle
        if len(colors) <= capacity:
            self.num_parts = len(colors)  # Number of parts in the bottle
            self.colors = colors  # List of colors used in the bottle
        else:
            self.num_parts = capacity
            self.colors = colors[:capacity]  # Only first capacity numbers of the list colors
        self.locked = self.is_locked()  # Is the bottle locked

    def top_color(self):
        if self.num_parts > 0:
            return self.colors[-1]  # Return the top color
        return None

    def is_empty(self):
        return self.num_parts == 0  # Check if the bottle is empty

    def is_full(self):
        return self.num_parts == self.capacity  # Check if the bottle is full

    def is_locked(self):
        return self.is_full() and all(color == self.colors[0] for color in self.colors)  # Check if the bottle is locked

    def pour_into(self, col):
        self.colors.append(col)
        self.num_parts += 1
        if self.num_parts == self.capacity:
            self.locked = self.is_locked() 
        return True
    
    def pour_from(self):
        if self.num_parts > 0:
            color = self.colors.pop()
            self.num_parts -= 1
            if self.num_parts == 0:
                self.locked = False
            return color
        return None

    def pour(self, other_bottle):
        if not self.is_empty() and not other_bottle.is_full():
            if other_bottle.is_empty() or (self.top_color() == other_bottle.top_color()):
                # Pouring logic
                other_bottle.pour_into(self.pour_from())  # Pour the top color into the other bottle
                return True
        return False  # Pouring failed

class Game:
    def __init__(self, total_bottles=6, empty_bottles=2, capacity=4):
        self.total_bottles = total_bottles  # Total number of bottles
        self.empty_bottles = empty_bottles  # Number of empty bottles
        self.capacity = capacity  # Capacity of each bottle
        Net_Color = ['lr', 'lg', 'lb', 'lo', 'lv','dr', 'dg', 'db', 'do', 'dv']  # List of colors used in the game
        self.colors = Net_Color  # List of colors used in the game
#        self.bottles = [Bottle(capacity) for _ in range(total_bottles)]  # List of bottles
        self.bottle_color_labels = []
        self.bottle_color_entries = []
        for i in range(self.total_bottles):
            if i < self.empty_bottles:
                self.bottle_color_entries.append([])  # Empty list for empty bottles
            else:
                self.bottle_color_entries.append(self.colors[:self.capacity])  

        self.steps = []
        self.create_form()  # Create the GUI form for user input

    def create_form(self):
        self.root = tk.Tk()
        self.root.title("Bottle Solver")
        self.create_input_fields()
        self.root.mainloop()

    def validate(self, ThisValue, DefaultValue=6, upper_limit=100):
        if ThisValue.isdigit() and 1 <= int(ThisValue) <= upper_limit:
            return int(ThisValue)
        else:
            return DefaultValue
        
    def create_input_fields(self):
        '''self.total_bottles_label = tk.Label(self.root, text="Total Bottles (default 6):")
        self.total_bottles_label.grid(row=1, column=0)
        self.total_bottles_entry = tk.Entry(self.root)
        self.total_bottles_entry.insert(0, self.total_bottles)  # Display default value
        self.total_bottles_entry.grid(row=1, column=1)

        self.empty_bottles_label = tk.Label(self.root, text="Empty Bottles:")
        self.empty_bottles_label.grid(row=2, column=0)
        self.empty_bottles_entry = tk.Entry(self.root)
        self.empty_bottles_entry.insert(0, self.empty_bottles)  # Display default value
        self.empty_bottles_entry.grid(row=2, column=1)
        self.total_bottles = self.validate(self.total_bottles_entry.get(), self.total_bottles)
        '''

        self.capacity_label = tk.Label(self.root, text="Capacity (per bottle):")
        self.capacity_label.grid(row=2, column=0)
        self.capacity_entry = tk.Entry(self.root)
        self.capacity_entry.insert(0, self.capacity)  # Display default value
        self.capacity_entry.grid(row=2, column=1)

        '''self.colors_label = tk.Label(self.root, text="Colors for Bottle (space-separated):")
        self.colors_label.grid(row=4, column=0)
        self.colors_entry = tk.Entry(self.root, width=50)
        self.colors_entry.insert(0, self.colors)  # Display default value
        self.colors_entry.grid(row=5, column=0, columnspan=2) 
        '''
        self.bottle_colors_label = tk.Label(self.root, text="Colors  Bottle wise (list of lists):")
        self.bottle_colors_label.grid(row=4, column=0)
        self.bottle_colors_entry = tk.Text(self.root, width=40, height=18)
 #       self.bottle_colors_entry.insert(0, self.bottle_color_entries)  # Display default value
        self.bottle_colors_entry.insert(tk.END, f"{self.bottle_color_entries}")
        self.bottle_colors_entry.grid(row=7, column=1, columnspan=2, rowspan=2) 

        self.solve_button = tk.Button(self.root, text="Solve", command=self.solve)
        self.solve_button.grid(row=0, column=0, columnspan=3),
        self.clear_button = tk.Button(self.root, text="Next", command=self.set_values)
        self.clear_button.grid(row=0, column=3, columnspan=3)

        self.result_text = tk.Text(self.root, height=20, width=50, padx=5, pady=5)
        self.result_text.grid(row=1, column=7, columnspan=5, rowspan=11)
        
      #  self.result_text.insert(tk.END, f"Colors: {self.colors}\n")
        self.result_text.insert(tk.END, f"Total Bottles: {self.total_bottles}\n")
        self.result_text.insert(tk.END, f"Empty Bottles: {self.empty_bottles}\n")
        self.result_text.insert(tk.END, f"Capacity: {self.capacity}\n") 
        self.result_text.insert(tk.END, f"Bottle wise colors: {self.bottle_color_entries}\n")
        
    def set_values(self):
        #self.empty_bottles = self.validate(self.empty_bottles_entry.get(), self.empty_bottles, self.total_bottles)
        #self.capacity = self.validate(self.capacity_entry.get(), self.capacity)
        #self.colors = self.colors_entry.get().split(" ")

        self.bottle_color_entries = eval(self.bottle_colors_entry.get("1.0", tk.END).strip())  # Convert the input string to a list
        self.total_bottles = len(self.bottle_color_entries) # Number of bottles from the input
        self.empty_bottles = sum(1 for botl in self.bottle_color_entries if len(botl)==0) # Count empty bottles from the input
        self.capacity = max(len(botl) for botl in self.bottle_color_entries )  # Get max capacity from the input
        self.working_bottle_entries = self.bottle_color_entries

        self.result_text.delete(1.0, tk.END)
        self.create_input_fields()

    def solve(self):
        for b in range(self.total_bottles):
            if len(self.working_bottle_entries[b]) > self.capacity:
                messagebox.showerror("Error", f"Bottle has more colors than capacity: {b}")
                return
            if len(self.working_bottle_entries[b]) <= self.capacity:
                #valid entry
                if len(self.working_bottle_entries[b]) == 0:
                    # Empty bottle = Universal Acceptor
                    continue
                elif len(self.working_bottle_entries[b]) == self.capacity and Bottle(self.capacity, self.working_bottle_entries[b]).is_locked():
                    # Full bottle = Locked if all colors are same
                        continue
                else :
                    # Can be a donor bottle so now find acceptor bottles
                    for a in range(self.total_bottles):
                        if a != b and len(self.working_bottle_entries[a]) < self.capacity:
                            # Check if the acceptor bottle is not the same as donor and has space
                            donor_bottle = Bottle(self.capacity, self.working_bottle_entries[b])
                            acceptor_bottle = Bottle(self.capacity, self.working_bottle_entries[a])
                            if donor_bottle.pour(acceptor_bottle):
                                # Pouring was successful
                                self.working_bottle_entries[b] = donor_bottle.colors
                                self.working_bottle_entries[a] = acceptor_bottle.colors
                                self.result_text.insert(tk.END, f"Step: Pour from Bottle {b} to Bottle {a}\n")
                                self.steps.append((b, a))  # Store the step for further processing
                                self.solve()  # Call the solve function again to check if the game is solved
                            else:
                                # Pouring was not successful, continue checking other bottles
                                continue
                    #Then last pour was bad, so undo the last pour
                    self.undo_pour(self.steps.pop())  
                    # This will remove the last step from the steps list



    def solve1(self):
        try:
            #self.total_bottles = int(self.total_bottles_entry.get())
            #self.empty_bottles = int(self.empty_bottles_entry.get())
            #self.capacity = int(self.capacity_entry.get())
            #colors = self.colors_entry.get().split(",")
#            if len(colors) != self.total_bottles - self.empty_bottles:
#                raise ValueError("Number of colors does not match number of bottles.")
            for i in range(self.total_bottles):
                if i < self.total_bottles - self.empty_bottles:
                    color = colors[i].strip()
                    if color not in self.colors:
                        raise ValueError(f"Invalid color: {color}")
                    self.bottles[i] = Bottle(self.capacity, [color]*self.capacity)
                else:
                    self.bottles[i] = Bottle(self.capacity, [])
            messagebox.showinfo("Success", "Game setup successfully.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))




if __name__ == "__main__":
    app = Game()
