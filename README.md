# Potstill Memory Generator

This is *Potstill*, an open source generator for standard cell based memories. It combines building blocks in the form of GDS cells into a fully placed and routed macro. The macro is compatible with and can be placed like any other standard cell. Timing and energy characteristics are precalculated for different sizes and interpolated upon memory generation. To ensure interoperability with the standard digital design flow, Potstill emits

- a GDS file containing the layout data
- a LEF file describing the interface to other standard cells
- multiple LIB files covering timing and energy characteristics for different operating conditions (corners)
- a simulation model
- a SPICE netlist and nodeset for LVS verification and transistor-level simulation

Potstill is written in Python to allow for easy modification and adjustments. It relies on a separate project, [Phalanx](https://github.com/fabianschuiki/phalanx), to process GDS data. Due to restrictions imposed by silicon foundries, no cell layouts can be published in the context of an open source project.


## Installation

To be able to properly use Potstill, you must clone the repository, move it to an installation location of your choice, and make `bin/postill` accessible in your path. The last step can be done either via symlink or adjustment of the `PATH` variable. For example:

    git clone https://github.com/fabianschuiki/potstill.git
    sudo mv potstill /usr/local/potstill
    sudo ln -s /usr/local/potstill/bin/potstill /usr/local/bin/potstill

Note that the generator currently requires a `umc65` folder to be present in its root directory, that is next to the `README.md` file.


## Usage

To generate a memory with `2**5 = 32` words of `32` bits each, type:

    potstill make 5 32

The output files can be generated individually via

    potstill make-gds ...
    potstill make-lef ...
    potstill make-lib ...
    potstill make-model ...
    potstill make-netlist ...
    potstill make-nodeset ...

To obtain a list of available subcommands, type:

    potstill

For detailed help of a specific command, type:

    potstill <command> -h


## Roadmap

The generator currently acts as an initial proof of concept. Its inner workings are focused on a specific 65nm process node. However, the generator can be adjusted to be more technology agnostic. Routing is one of the major shortcomings, with the designer having to provide all but the simplest routes themself in the form of additional GDS cells. With minimal effort Potstill or Phalanx can be adjusted to automated routing guided by the designer, e.g. by assigning routing tracks to be used. A* comes to mind.

The file `bin/main.py` contains some leftover code concerning the characterization of macros and should be moved into appropriate `commands/*.py` and `potstill/*.py` files.
