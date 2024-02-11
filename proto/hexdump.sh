cat hex | cut -c 15- | sed 's/0x//g' | tr '\n' ' ' | sed 's/ //g' > out
