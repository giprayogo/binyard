#!/bin/bash

data_file=$1
printf "$data_file\n3\n0 1 2\n" | extrapolate_tau
