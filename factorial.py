import time
import numpy as np
from flask import Flask, request, jsonify
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def time_complexity_visualizer(algorithm, n_min, n_max, n_step):
    times = []
    inputs_sizes = list(range(n_min, n_max + 1, n_step))

    plt.ion()
    fig, ax = plt.subplots()
    ax.set_xlabel('Input Size')
    ax.set_ylabel('Running Time (seconds)')
    ax.set_title('Algorithm Time Complexity Visualizer (live)')
    line, = ax.plot([], [], 'o-')

    for i, n in enumerate(inputs_sizes):
        start_time = time.time()
        algorithm(n)
        end_time = time.time()
        times.append(end_time - start_time)

        line.set_data(inputs_sizes[:i + 1], times)
        ax.relim()
        ax.autoscale_view()
        plt.draw()
        plt.pause(0.01)

    plt.ioff()
    plt.show(block=True)

    filename = f"{algorithm._name_}.png"
    fig.savefig(filename)

    return filename



def linear_search(n):
    
    for i in range(n * 1000):
        pass


def bubble_sort(n):
    for i in range(n):
        for j in range(n - 1):
            pass


def binary_search(n):
