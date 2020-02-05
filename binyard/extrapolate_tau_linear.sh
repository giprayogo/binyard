#!/bin/bash

data_file=$1
printf "$data_file\n2\n0 1\n" | extrapolate_tau
