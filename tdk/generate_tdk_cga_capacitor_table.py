import xlwt
import re


def format_capacitance(capacitance):
    """
    Format the capacitance value

    Parameters:
    capacitance (float): Capacitance in picofarads

    Returns:
    str: Formatted capacitance string
    """
    if capacitance < 1000:  # less than 1nF
        return str(capacitance).rstrip('0').rstrip('.') + 'pF'
    elif capacitance < 1e6:  # less than 1uF
        capacitance /= 1000  # convert to nF
        return str(capacitance).rstrip('0').rstrip('.') + 'nF'
    else:
        capacitance /= 1e6  # convert to uF
        return str(capacitance).rstrip('0').rstrip('.') + 'uF'


# Define mappings
dimensionseia = {'1': '0201', '2': '0402', '3': '0603', '4': '0805', '5': '1206', '6': '1210', '8': '1812', '9': '2220'}
dimensionsmetric = {'1': '0603', '2': '1005', '3': '1608', '4': '2012', '5': '3216', '6': '3225', '8': '4532', '9': '5750'}
thickness = {'A': '0.30', 'B': '0.50', 'C': '0.60', 'E': '0.80', 'F': '0.85', 'H': '1.15', 'J': '1.25', 'L': '1.60', 'M': '2.00', 'N': '2.30', 'P': '2.50', 'Q': '2.80', 'R': '3.20'}
thicknesscode = {'A': '03', 'B': '05', 'C': '06', 'E': '08', 'F': '085', 'H': '115', 'J': '125', 'L': '16', 'M': '20', 'N': '23', 'P': '25', 'Q': '28', 'R': '32'}
voltage_test_condition = {'1': '1', '2': '2', '3': '3'}
temperature_range = {'C0G': '–55:125', 'X5R': '–55:85', 'X7R': '–55:125', 'X7S': '–55:125', 'X7T': '–55:125'}
temperature_coefficient = {'C0G': '+/-30', 'X5R': '+/-15%', 'X7R': '+/-15%', 'X7S': '+/-22%', 'X7T': '+22%/-33%'}
rated_voltage = {'0E': '2.5V', '0G': '4V', '0J': '6.3V', '1A': '10V', '1C': '16V', '1E': '25V', '1V': '35V', '1H': '50V', '1N': '75V'}
tolerance = {'C': '+/-0.25', 'D': '+/-0.50', 'J': '5%', 'K': '10%', 'M': '20%'}
packaging_style = {'A': 'A', 'B': 'B', 'K': 'K'}
reserved = {'A': 'A', 'B': 'B', 'C': 'C'}

# Create workbook and add sheet
workbook = xlwt.Workbook()
worksheet = workbook.add_sheet('CGA')

# Add headers to the Excel file
worksheet.write(0, 0, 'Comment')
worksheet.write(0, 1, 'Description')
worksheet.write(0, 2, 'MFG')
worksheet.write(0, 3, 'MPN')
worksheet.write(0, 4, 'Value')
worksheet.write(0, 5, 'Tolerance')
worksheet.write(0, 6, 'Tcr')
worksheet.write(0, 7, 'Tr')
worksheet.write(0, 8, 'Qual')
worksheet.write(0, 9, 'Voltage')
worksheet.write(0, 10, 'Library Path')
worksheet.write(0, 11, 'Library Ref')
worksheet.write(0, 12, 'Footprint Path')
worksheet.write(0, 13, 'Footprint Ref')
worksheet.write(0, 14, 'Footprint Path 2')
worksheet.write(0, 15, 'Footprint Ref 2')
worksheet.write(0, 16, 'Footprint Path 3')
worksheet.write(0, 17, 'Footprint Ref 3')

footprints = []

with open('tdk_automotive_pn.csv', 'r') as f:
    for i, line in enumerate(f.readlines(), start=1):
        # Strip any white space
        part_number = line.strip()

        # Breakdown the part number into its components
        series = part_number[0:3]
        dim = dimensionseia[part_number[3]]
        package = "CAPC" + dimensionsmetric[part_number[3]] + "X" + thicknesscode[part_number[4]]
        tcode = thickness[part_number[4]]
        vtc = voltage_test_condition[part_number[5]]
        dielectric = part_number[6:9]
        tr = temperature_range[dielectric]
        tcr = temperature_coefficient[dielectric]
        rv = rated_voltage[part_number[9:11]]

        # Parse capacitance
        capcode = part_number[11:14]
        if 'R' in capcode:
            cap = float(capcode.replace('R', '.'))
        else:
            cap = float(capcode[0:2]) * (10 ** int(capcode[2]))
        
        tol = tolerance[part_number[14]]
        thick = part_number[15:18]
        pack = packaging_style[part_number[18]]
        res = reserved[part_number[19]]

        # Write data to Excel file
        worksheet.write(i, 0, part_number)
        description = "CAPACITOR CERAMIC " + format_capacitance(cap).upper() + " " + tol + " " + rv + " " + dielectric + " " + dim
        worksheet.write(i, 1, description)
        worksheet.write(i, 2, "TDK")
        worksheet.write(i, 3, part_number)
        worksheet.write(i, 4, format_capacitance(cap))
        worksheet.write(i, 5, tol)
        worksheet.write(i, 6, tcr)
        worksheet.write(i, 7, tr)
        worksheet.write(i, 8, "AEC-Q200")
        worksheet.write(i, 9, rv)
        worksheet.write(i, 10, "tdk.SchLib")
        worksheet.write(i, 11, "CAP")
        worksheet.write(i, 12, "tdk.PcbLib")
        worksheet.write(i, 13, package + "N")
        worksheet.write(i, 14, "tdk.PcbLib")
        worksheet.write(i, 15, package + "L")
        worksheet.write(i, 16, "tdk.PcbLib")
        worksheet.write(i, 17, package + "M")

        footprints.append(package + "N")
        footprints.append(package + "L")
        footprints.append(package + "M")

print("all footprints:" + sorted(list(set(footprints))))

# Save workbook
workbook.save('tdk.xls')
