from config.constants import HUBBLE_CONSTANT
from src.data_manipulation import find_even_numbers, reverse_strings

if __name__ == '__main__':
    input_strings = ['hello', 'world']
    reversed_result = reverse_strings(input_strings)
    print('Reversed Result:', reversed_result)

    input_numbers = [0, 1, 2, 3, 4, 5]
    even_numbers = find_even_numbers(input_numbers)
    print('Even Numbers:', even_numbers)

    print('The answer to Life, the Universe and everything is', HUBBLE_CONSTANT)
