# Example: sed -i -E -f cleanup.sed ../path/filename.txt

# Remove all lines starting with these patterns
/^\&/d
/^\-/d
/^_/d
/^http/d

# Remove all lines starting with numbers
/^[0-9]/d

# Remove all lines that has less than 16 characters
/^.{,16}$/d
