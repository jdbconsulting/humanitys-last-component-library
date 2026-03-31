def process_file(input_file, output_file):
    try:
        with open(input_file, 'r') as file:
            lines = file.readlines()
            numbers = [float(line.strip()) for line in lines if line.strip().replace('.', '', 1).isdigit()]
    except FileNotFoundError:
        print("The file was not found.")
        return

    unique_numbers = list(set(numbers))  # remove duplicates
    unique_numbers.sort()  # sort in ascending order

    with open(output_file, 'w') as file:
        for number in unique_numbers:
            # write to output file with the same format as input (integers as int, floats as float)
            if number.is_integer():
                file.write(f"{int(number)}\n")
            else:
                file.write(f"{number}\n")


# replace 'input.txt' and 'output.txt' with your actual file names
process_file('e24_e96_combined.txt', 'output.txt')


