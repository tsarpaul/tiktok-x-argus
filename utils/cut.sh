#!/bin/sh
cat string | cut -c 14- | sed 's/0x//g' | sed 's/ //g' | tr -d '\n'
