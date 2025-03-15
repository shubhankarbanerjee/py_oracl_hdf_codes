from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy import Config

# Set OpenGL version to 1.1
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'gl_backend', 'gl')
Config.set('graphics', 'gl_backend_version', '1.1')

class TangoSolverGUI(App):
    def build(self):
        self.title = 'Tango Solver GUI'
        layout = BoxLayout(orientation='vertical')

        self.label = Label(text='Enter numbers (comma separated):')
        layout.add_widget(self.label)

        self.text_input = TextInput(multiline=False)
        layout.add_widget(self.text_input)

        self.result_label = Label(text='')
        layout.add_widget(self.result_label)

        button_layout = GridLayout(cols=2, size_hint_y=None, height=50)
        self.validate_button = Button(text='Validate')
        self.validate_button.bind(on_press=self.validate_numbers)
        button_layout.add_widget(self.validate_button)

        self.print_button = Button(text='Print Tango')
        self.print_button.bind(on_press=self.print_tango)
        button_layout.add_widget(self.print_button)

        layout.add_widget(button_layout)

        return layout

    def validate_numbers(self, instance):
        numbers = list(map(int, self.text_input.text.split(',')))
        if validate_tango(numbers):
            self.result_label.text = 'Valid Tango'
        else:
            self.result_label.text = 'Invalid Tango'

    def print_tango(self, instance):
        numbers = list(map(int, self.text_input.text.split(',')))
        self.result_label.text = '\n'.join([print_binary_with_spaces(num) for num in numbers])

def print_binary_with_spaces(number):
    binary_str = format(number, '06b')
    spaced_binary_str = ' '.join(binary_str)
    return spaced_binary_str

def validate_number(number):
    ones = 0
    binary_str = format(number, '06b')
    ones = binary_str.count('1')
    zeroes = binary_str.count('0')
    return ones == 3 and zeroes == 3 and not ('111' in binary_str)

def validate_tango(numbers):
    valid = True
    for bit_position in range(6):
        ones = 0
        for number in numbers:
            ones += get_bit(number, bit_position)
        valid = valid and ones == 3 
        if not valid:
            break
    for bit_position in range(6):
        for i in range(4):
            valid = valid and not (get_bit(numbers[i], bit_position)==get_bit(numbers[i+1], bit_position)
                                      ==get_bit(numbers[i+2], bit_position)==1)
    for number in numbers:
        valid = valid and validate_number(number)
        if not valid:
            break
    return valid

def get_bit(number, position):
    return (number >> position) & 1

if __name__ == '__main__':
    TangoSolverGUI().run()