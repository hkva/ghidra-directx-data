#!/bin/sh
(
    mkdir -p generated
    cd generated
    ../generate.py d3d8  32
    ../generate.py d3d9  32
    ../generate.py d3d10 32
    ../generate.py d3d11 32
    ../generate.py d3d12 32
)
