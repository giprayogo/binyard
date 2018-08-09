""" A better autorunner """

import time
import os
import argparse

parser = argparse.ArgumentParser(description='Automatically fetch and toss jobs specified in joblist')
parser.add_argument("-a", "--anything", 
                  help="Any kind of help please"

class Job:
    def __init__(self, root=None, interval=None, count=None):
        self.root = None if root is None else root
        self.interval = None if root is None else interval
        self.count = None if root is None else count
        self.finished = False
        self.counter = 0
    def add_count(self):
        self.counter += 1
        self.finished = True if self
def get_output(job):
    return None
def finished_output(job):
    return None
def in_queue(job):
    return None
def write_log:
    return None
def write_status_file:
    return None
def killed:
    return None
def parse_job_file(filename):
    """ Return list of Job specified in jobfile """
    try:
        jobfile = open(filename, 'r')
        for line in out.readlines():
            args = line.split()

    return None

while not killed():
    jobs = parse_job_file(thejobfile)
    for job in jobs:
    try:
        get_output(job)
        if ( not in_queue(job) and finished_output(job) ):
            job.fetch
            job.add_count()
            if not job.finished():
                job.toss
        else:
        
    except NetworkError:
        time.sleep()

