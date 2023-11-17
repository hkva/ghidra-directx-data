#!/bin/sh
(
    mkdir -p generated
    cd generated
    ../generate.py d3d8  64
    ../generate.py d3d9  64
    ../generate.py d3d10 64
    ../generate.py d3d11 64
    ../generate.py d3d12 64
)
