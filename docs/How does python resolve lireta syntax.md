# How does python resolve lireta syntax
Let's take an example:
```
simult {
	instr = std.sin;
	seq {gliss A B;} {note G; note F;};
}{
	note A++;
};
```
Fist, python will parse the string and break down into blocks, that will look like:
```python
[
    [
        "simult",
        [
            ["instr", "=", "std.sin"],
            [
                "seq",
                [["gliss", "A", "B"]],
                [["note", "G"], ["note", "F"]],
            ],
        ],
        [["note", "A++"]],
    ]
]

```

Notice that each "line" (broken down by `;`) ends up in a separate list, and each block (between `{` and `}`) are also in a separate list.

This makes blocks with only one line to be lists with a sigle element, that is a list of a single element itself.

Let's focus on a single line now:
```
seq {gliss A B;}{note G; note F;};
```
Its corresponding list in python is
```python
[
    "seq",
    [["gliss", "A", "B"]],
    [["note", "G"], ["note", "F"]],
]
```
The next step is the evaluation of lines. Each line must start with a string (`str` in python). In our case, we can see four lines, with the starting strings `"seq"`, `"gliss"`, `"note"` and `"note"` again.

These are called keywords in lireta, and they are essentially functions that will evaluate what follows them. The output of these keywords can be:

- `None`: keyword does not return. Instead, it might change a variable, for example.
- `AudioWave`: class in lireta, that stores the audio signal.
- `str`: the keyword evaluates the parameters to a string, that will probably be the parameter for a keyword later.
- Another line: similar to the `str` return type, but it allows for whole blocks to be in there.

Notice that, in our example, the keyword `"seq"` has parameters that are lists (lines). However, `"seq"` expects `str` or `AudioWave`, so it needs to make these lines to be evaluated first.

This might not be the case for keywords such as `"section"` that are be able to handle blocks.

Now we need to evaluate `[["gliss", "A", "B"]]`. Since it is a list of a single element, it evaluates to the single element: `["gliss", "A", "B"]`.

`"gliss"` will now use its parameters (`"A"` and `"B"`) and produce an AudioWave that we will call `w0`.

By a similar process, the `"note"` keywords will produce `w1` and `w2`.

In the block `{note G; note F;}`, we have two AudioWaves but no keyword. Lireta will understand this as a `"seq"` call by default, and produce `w3`.

Here it's also important to say that a line with only an unmapped string (not associated to a keyword) will be defaulted as a parameter for `"note"`.

With `w0` and `w3`, `"seq"` will produce `w4`.

One requirement for a lireta script to be valid is to produce an `AudioWave` after all the resoutions. If a script evaluates to a string, for example, it is not valid script.
