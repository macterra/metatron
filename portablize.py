def inplace_change(filename, old_string, new_string):
    # Safely read the input filename using 'with'
    with open(filename) as f:
        s = f.read()
        if old_string not in s:
            print(f"'{old_string}' not found in {filename}.")
            return

    # Safely write the changed content, if found in the file
    with open(filename, 'w') as f:
        print(f"Changing '{old_string}' to '{new_string}' in {filename}")
        s = s.replace(old_string, new_string)
        f.write(s)

inplace_change('_site/index.html', 'href="/', 'href="')
inplace_change('_site/index.html', 'src="/', 'src="')