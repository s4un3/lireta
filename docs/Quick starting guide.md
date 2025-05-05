# Quick-start guide

This document explains the basics of lireta syntax and prepares to write your first script. 

## Types

In lireta, there are mainly 3 types of data:

- Audio
- String
- Null (None)

## Blocks, lines and keywords

A lireta script will consist in lines, separated by `;`, blocks, delimited by `{` and `}`, and keywords, that are the starting element in a line.

For example:

```
print {var octave;};
```

Here we have a line `print {var octave;};` and a block `{var octave;}` with a single line `var octave;` inside it.

Lireta will try to solve lines by matching the first entry with the names of keywords. In the example, it will match `print`, and pass `{var octave;}` as parameter for `print`.

Since `print` expects strings, it will try solving that block, and the line `var octave;` will then be processed.

The block has only one line, so the result of the line is the result of the block.

If a block has more than one line, an implicit call of `seq` or `string` will be used, based on the types that the lines returned. These keywords, respectivelly, arrange the audio in sequential mode, and concatenates strings.

If there are incompatible types (both audio and string), it will cause an error.

For example:

```
simult {
	C;
	E;
	G;
}{
	C-;
	E-;
	G-;
};
```

Each block here has multiple lines, and all the lines in the block have compatible types. Since they are audios, an implicit `seq` will be called, using the notes `C`, `E`, `G` for the first block, and `C-`, `E-`, `G-` for the second.

## Note names

A valid note name consists of:

- An obligatory "base": `A`, `B`, `C`, `D`, `E`, `F` or `G`.
- Optional accidentals: `#` for sharp and `b` for flat, stackable.
- Optional cents adjustment: `(`, `+` or `-`, a number, `c` and `)`.
- Optional octave settings, that can be:
    * Relative: `+` for one octave higher than the default, `-` for one lower, stackable.
    * Absolute: an integer number. Use `~` to mark if it is negative.
   
Underscores denote pauses, and a number followed by `Hz` is another way to set up a note.

For example:

```
C
D#
E(+15.9c)
F+
G5
A~10
_
440Hz
```

A note like `D#b#b#b###bbb(-62485.236587c)++--+++-+++--` is unecessarily complex, but still valid.