def convert_resistance_to_float(resistances):
    # Dictionary to map units to their respective multipliers
    unit_dict = {
        'Ohms': 1,
        'kOhms': 1e3,
        'MOhms': 1e6
    }

    # List to store converted resistances
    converted_resistances = []

    for resistance in resistances:
        # Split the resistance value and its unit
        value, unit = resistance.split()

        # Convert value to float and multiply by appropriate unit
        float_value = float(value) * unit_dict[unit]

        # Add converted value to the list
        converted_resistances.append(float_value)

    # Sort the converted resistances
    sorted_resistances = sorted(converted_resistances)

    # Format to remove trailing zeros
    formatted_resistances = ['{0:g}'.format(val) for val in sorted_resistances]
    
    return formatted_resistances

# Test the function
resistances = ["240 Ohms", "47 kOhms", "4.7 kOhms", "2.2 kOhms", "22 Ohms", "33 Ohms", "15 kOhms", "1 kOhms", "100 kOhms", "4.99 kOhms", "100 Ohms", "200 Ohms", "1 MOhms", "49.9 kOhms", "2 kOhms", "10 kOhms", "499 kOhms", "41.2 Ohms", "158 Ohms", "294 Ohms", "37.4 Ohms", "4.3 kOhms", "71.5 Ohms", "17.8 Ohms", "68 Ohms", "62 Ohms", "470 Ohms", "22 kOhms", "27 Ohms", "12 kOhms", "560 kOhms", "330 Ohms", "160 Ohms", "51 Ohms", "180 Ohms", "5.6 kOhms", "33 kOhms", "470 kOhms", "1.2 kOhms", "12 Ohms", "47 Ohms", "680 Ohms", "330 kOhms", "820 Ohms", "68 kOhms", "910 Ohms", "240 kOhms", "1.6 kOhms", "160 kOhms", "560 Ohms", "5.1 kOhms", "30 kOhms", "430 Ohms", "510 kOhms", "36 Ohms", "220 kOhms", "1.8 kOhms", "30 Ohms", "16 kOhms", "510 Ohms", "3.6 kOhms", "120 kOhms", "6.8 kOhms", "82 Ohms", "56 Ohms", "120 Ohms", "3.9 kOhms", "390 Ohms", "27 kOhms", "931 kOhms", "3 kOhms", "24 Ohms", "39 kOhms", "43 Ohms", "8.2 kOhms", "82 kOhms", "360 Ohms", "43 kOhms", "430 kOhms", "620 Ohms", "820 kOhms", "665 kOhms", "4.22 kOhms", "3.3 kOhms", "620 kOhms", "2.4 kOhms", "13 Ohms", "150 Ohms", "24.9 kOhms", "52.3 Ohms", "33.2 Ohms", "75 Ohms", "300 Ohms", "51 kOhms", "91 kOhms", "750 Ohms", "118 kOhms", "1.5 kOhms", "221 Ohms", "3.4 kOhms", "698 Ohms", "31.6 kOhms", "464 kOhms", "33.2 kOhms", "40.2 Ohms", "16.9 kOhms", "18 kOhms", "150 kOhms", "680 kOhms", "1.21 kOhms", "40.2 kOhms", "2.49 kOhms", "22.1 Ohms", "53.6 kOhms", "15 Ohms", "60.4 kOhms", "301 kOhms", "86.6 kOhms", "511 Ohms", "5.49 kOhms", "25.5 kOhms", "51.1 Ohms", "60.4 Ohms", "249 kOhms", "12.1 kOhms", "243 kOhms", "3.01 kOhms", "5.62 kOhms", "90.9 kOhms", "402 Ohms", "56 kOhms", "18.2 Ohms", "16 Ohms", "130 kOhms", "270 kOhms", "187 Ohms", "9.1 kOhms", "2.55 kOhms", "910 kOhms", "3.57 kOhms", "95.3 Ohms", "28 kOhms", "11.5 kOhms", "26.1 kOhms", "649 Ohms", "1.91 kOhms", "7.5 kOhms", "22.6 Ohms", "221 kOhms", "301 Ohms", "274 kOhms", "10.2 kOhms", "1.82 kOhms", "13.3 kOhms", "140 Ohms", "147 Ohms", "2.21 kOhms", "39 Ohms", "27.4 Ohms", "27.4 kOhms", "35.7 Ohms", "41.2 kOhms", "8.06 kOhms", "178 kOhms", "39.2 Ohms", "121 Ohms", "63.4 kOhms", "1.65 kOhms", "30.1 Ohms", "332 Ohms", "604 kOhms", "9.53 kOhms", "61.9 Ohms", "121 kOhms", "280 Ohms", "44.2 kOhms", "84.5 kOhms", "110 kOhms", "133 Ohms", "3.92 kOhms", "4.87 kOhms", "300 kOhms", "511 kOhms", "91 Ohms", "71.5 kOhms", "36.5 Ohms", "19.1 kOhms", "1.43 kOhms", "12.4 kOhms", "316 kOhms", "39.2 kOhms", "4.64 kOhms", "5.36 kOhms", "54.9 Ohms", "549 Ohms", "16.5 kOhms", "165 kOhms", "32.4 kOhms", "324 kOhms", "37.4 kOhms", "47.5 kOhms", "9.09 kOhms", "105 kOhms", "56.2 kOhms", "75 kOhms", "2.15 kOhms", "215 Ohms", "5.76 kOhms", "634 kOhms", "95.3 kOhms", "1.24 kOhms", "16.2 kOhms", "2.1 kOhms", "226 kOhms", "604 Ohms", "76.8 kOhms", "51.1 kOhms", "8.45 kOhms", "140 kOhms", "18 Ohms", "34 Ohms", "4.53 kOhms", "365 kOhms", "866 Ohms", "196 kOhms", "147 kOhms", "143 Ohms", "158 kOhms", "2.26 kOhms", "309 kOhms", "34 kOhms", "34.8 kOhms", "10.7 kOhms", "2.43 kOhms", "36.5 kOhms", "30.1 kOhms", "1.33 kOhms", "102 kOhms", "287 Ohms", "34.8 Ohms", "42.2 Ohms", "54.9 kOhms", "562 kOhms", "6.65 kOhms", "68.1 kOhms", "52.3 kOhms", "42.2 kOhms", "332 kOhms", "249 Ohms", "130 Ohms", "14.3 kOhms", "36 kOhms", "17.8 kOhms", "6.2 kOhms", "182 kOhms", "261 kOhms", "35.7 kOhms", "412 Ohms", "64.9 kOhms", "2.32 kOhms", "7.87 kOhms", "127 Ohms", "475 kOhms", "6.19 kOhms", "3.24 kOhms", "107 Ohms", "13 kOhms", "169 Ohms", "26.7 kOhms", "294 kOhms", "324 Ohms", "46.4 kOhms", "66.5 Ohms", "698 kOhms", "73.2 Ohms", "787 kOhms", "80.6 kOhms", "255 kOhms", "3.16 kOhms", "28.7 kOhms", "2.37 kOhms", "124 Ohms", "13.7 kOhms", "133 kOhms", "2.61 kOhms", "20.5 kOhms", "6.49 kOhms", "68.1 Ohms", "1.27 kOhms", "1.69 kOhms", "110 Ohms", "182 Ohms", "267 kOhms", "32.4 Ohms", "374 Ohms", "453 kOhms", "5.23 kOhms", "57.6 kOhms", "6.98 kOhms", "665 Ohms", "7.68 kOhms", "715 kOhms", "80.6 Ohms", "93.1 kOhms", "26.1 Ohms", "9.76 kOhms", "61.9 kOhms", "10.5 kOhms", "845 Ohms", "1.15 kOhms", "1.62 kOhms", "102 Ohms", "174 Ohms", "174 kOhms", "2.94 kOhms", "274 Ohms", "3.09 kOhms", "38.3 kOhms", "383 kOhms", "4.32 kOhms", "402 kOhms", "47.5 Ohms", "487 Ohms", "806 Ohms", "806 kOhms", "887 Ohms", "14.7 kOhms", "82.5 Ohms", "107 kOhms", "2.8 kOhms", "2.87 kOhms", "23.7 kOhms", "31.6 Ohms", "4.12 kOhms", "7.32 kOhms", "825 Ohms", "78.7 Ohms", "16.5 Ohms", "127 kOhms", "154 kOhms", "21 kOhms", "210 Ohms", "357 kOhms", "412 kOhms", "475 Ohms", "536 kOhms", "88.7 kOhms", "11 kOhms", "45.3 kOhms", "48.7 Ohms", "11 Ohms", "11.3 kOhms", "11.8 kOhms", "14 kOhms", "210 kOhms", "215 kOhms", "29.4 kOhms", "30.9 Ohms", "442 Ohms", "56.2 Ohms", "576 kOhms", "681 kOhms", "7.15 kOhms", "78.7 kOhms", "82.5 kOhms", "90.9 Ohms", "909 kOhms", "1.05 kOhms", "1.18 kOhms", "1.54 kOhms", "115 Ohms", "12.4 Ohms", "205 Ohms", "21.5 kOhms", "226 Ohms", "23.7 Ohms", "3.74 kOhms", "340 Ohms", "365 Ohms", "43.2 kOhms", "63.4 Ohms", "69.8 kOhms", "73.2 kOhms", "1.02 kOhms", "1.4 kOhms", "1.13 kOhms", "1.37 kOhms", "191 Ohms", "243 Ohms", "30.9 kOhms", "48.7 kOhms", "487 kOhms", "931 Ohms", "5.11 kOhms", "191 kOhms", "1.78 kOhms", "11.5 Ohms", "115 kOhms", "12.7 kOhms", "187 kOhms", "23.2 Ohms", "732 kOhms", "953 Ohms", "28.7 Ohms", "124 kOhms", "1.1 kOhms", "1.96 kOhms", "14 Ohms", "15.8 kOhms", "162 kOhms", "21.5 Ohms", "348 Ohms", "392 kOhms", "5.9 kOhms", "523 Ohms", "619 kOhms", "76.8 Ohms", "86.6 Ohms", "976 Ohms", "18.7 kOhms", "162 Ohms", "143 kOhms", "1.87 kOhms", "24.3 Ohms", "24.3 kOhms", "340 kOhms", "53.6 Ohms", "6.34 kOhms", "649 kOhms", "66.5 kOhms", "23.2 kOhms", "118 Ohms", "19.6 kOhms", "232 kOhms", "25.5 Ohms", "316 Ohms", "4.02 kOhms", "45.3 Ohms", "464 Ohms", "562 Ohms", "69.8 Ohms", "787 Ohms", "8.66 kOhms", "8.87 kOhms", "845 kOhms", "93.1 Ohms", "1.47 kOhms", "1.58 kOhms", "113 kOhms", "13.3 Ohms", "237 kOhms", "3.48 kOhms", "309 Ohms", "357 Ohms", "442 kOhms", "523 kOhms", "590 kOhms", "64.9 Ohms", "732 Ohms", "953 kOhms", "453 Ohms", "22.1 kOhms", "178 Ohms", "2.05 kOhms", "237 Ohms", "280 kOhms", "383 Ohms", "422 Ohms", "422 kOhms", "768 kOhms", "84.5 Ohms", "976 kOhms", "200 kOhms", "169 kOhms", "549 kOhms", "16.9 Ohms", "12.1 Ohms", "165 Ohms", "2.67 kOhms", "348 kOhms", "57.6 Ohms", "619 Ohms", "715 Ohms", "887 kOhms", "18.2 kOhms", "267 Ohms", "374 kOhms", "38.3 Ohms", "43.2 Ohms", "137 Ohms", "16.2 Ohms", "17.4 Ohms", "17.4 kOhms", "196 Ohms", "205 kOhms", "255 Ohms", "28 Ohms", "3.83 kOhms", "590 Ohms", "9.31 kOhms", "97.6 kOhms", "232 Ohms", "59 Ohms", "432 Ohms", "576 Ohms", "1.07 kOhms", "6.81 kOhms", "88.7 Ohms", "26.7 Ohms", "15.8 Ohms", "11.8 Ohms", "46.4 Ohms", "11.3 Ohms", "21 Ohms", "19.1 Ohms", "12.7 Ohms", "19.6 Ohms", "29.4 Ohms", "10.7 Ohms", "20.5 Ohms", "14.7 Ohms", "97.6 Ohms", "14.3 Ohms", "10 Ohms", "49.9 Ohms", "20 kOhms", "499 Ohms", "8.25 kOhms", "1.74 kOhms", "2.74 kOhms", "6.04 kOhms", "15.4 kOhms", "432 kOhms", "154 Ohms", "866 kOhms", "137 kOhms", "1.3 kOhms", "360 kOhms", "22.6 kOhms", "390 kOhms", "20 Ohms", "261 Ohms", "825 kOhms", "113 Ohms", "18.7 Ohms", "634 Ohms", "270 Ohms", "180 kOhms", "909 Ohms", "15.4 Ohms", "10.2 Ohms", "24.9 Ohms", "59 kOhms", "4.75 kOhms", "2.7 kOhms", "768 Ohms", "105 Ohms", "10.5 Ohms", "681 Ohms", "24 kOhms", "3.65 kOhms", "62 kOhms", "750 kOhms", "4.42 kOhms", "287 kOhms", "3.32 kOhms", "392 Ohms", "44.2 Ohms", "536 Ohms", "220 Ohms", "13.7 Ohms"]

def save_to_file(values, filename):
    with open(filename, 'w') as f:
        for value in values:
            f.write(str(value) + '\n')

# Convert the resistances to float and sort them
converted_resistances = convert_resistance_to_float(resistances)

# Display
print(converted_resistances)

# Save the converted resistances to a file
save_to_file(converted_resistances, 'output.txt')


