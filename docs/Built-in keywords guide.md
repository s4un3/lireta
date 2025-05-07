# Lireta keywords

This document explains the syntax of the built-in keywords of lireta, alongside some examples.

## `seq`

### Usage

```
seq [...]
```

Takes audio inputs, creates and returns a sequential audio.

### Examples

```
seq C D E F;
seq {seq C D E;} F;
```

Note that `note` is being called implicitily due to the note names.

## `note`

### Usage

```
note value [duration];
```

Reads from variables: `duration`, `octave`, `instrument`, `bpm`, `intensity`.

Takes a note name, creates and returns the corresponding audio. `duration` overrides the usage of the variable `duration`.

### Examples

```
note Eb 0.5;
```

## `simult`

### Usage

```
simult [...];
```

Takes audio inputs, creates and returns a simultaneous audio.

### Examples

```
simult C E G;
```
```
simult {
	seq C D E F G A B C+;
}{
	seq C- E- G-;
};
```

## `var`

### Usage

```
var name; # 1
var name = value; # 2
var name := value; # 3
```

(1) Acess and returns the value of the variable with the corresponding name.

(2) Assigns a value to the variable, and creates an error if it has not been declared yet. Search in parents scopes too.

(3) Declares a variable in the current scope and assigns a value.

### Examples
```
var x := 10;
var bpm = 100;
print {var x;};
```

## `print`

### Usage

```
print [...];
```

Prints strings.

### Examples

```
print "Hello World!";
print "bpm = " {var bpm;};
```

## `sfx`

### Usage

```
sfx name [duration];
```

Reads from variables: `duration`, `bpm`, `intensity`.

Creates and returns an audio sample with a pitchless instrument **without** changing the variable `instrument`. The parameters `duration` overrides the usage of the variable `duration`.

The instrument in the parameter must be a pitchless instrument.

### Examples

```
sfx bell;
```

## `loop`

### Usage

```
loop number {...}; # 1
loop number name {...}; # 2
```

(1) Returns the block repeated `number` times.
(2) Returns the block repeated `number` times, with the variable `name` accessible within the loop, starting at 0 and incrementing every step.

### Examples

```
loop 50 C;
loop 3 {
	seq A- B- C D;
};
loop 5 i {
	print {var i;} "\n";
};
```

## `func`

Usage:

```
func (!) f; # 1
func (!) f : ...; # 2
func (!) f = {...}; # 3
func (!) f := {...}; # 4
func (!) f : ... = {...}; # 5
func (!) f : ... := {...}; # 6
```

(1) Calls the function without any parameters.

(2) Calls the function with the informed parameters.

(3) Assigns a new parameterless function to an existing function.

(4) Declares a parameterless function.

(5) Assigns a new function (with parameters) to an existing function.

(6) Declares a function (with parameters).

The parameter `!` denotes that the function is "unclean", meaning it executes on the calling scope, not in the original one.

### Examples

Examples here will have comments explaining them due to the complexity of this keyword.

Parameters will be variable names, and they are separated by space:

```
func f : x y z = {
	{var x;};
};
```

Functions will automatically carry references to the variables in their parent scope:

```
func playm := {.;};
func setm := {.;};

{
	var m := D;
	func playm = {
		note {var m;};
	};
	func setm : x = {
		var m = {var x;};
	};
};

# now even if 'm' is inacessible directly,
func playm; # will play D;
func setm : C;
func playm; # will play C;
```

Similarly, functions that depend on variables outside their own scope can have their operation impacted by changes in those variables:

```
var t := 0;
func ! h : v := {
	note {var v;} {var t;}; # uses t=0
};
var t = 4; # now h uses t=4
```

It also can modify or read variables from the calling scope:

```
func f := {.;};

{
	# x was not even declared until now
	func ! f = {
		print {var x;};
	};
};

var x := 10;
func f; # will still be able to reach x=10
```

On the difference between clean and unclean functions, as mentioned before, unclean functions are executed in the calling scope, or more accuratelly, on a child of the calling scope, while clean functions are executed in a child of the declaring/assigning scope.

If a function needs to modify or read a variable that is not in the parameters but in the assigning scope, it should be a clean function, while if it operates closer to a macro, needing to modify or read from the calling scope, it should be a unclean function.

As the name suggest, avoid using unclean functions.

When a function could have mixed behaviour, an unclean wrapper that calls the clean and parts can be constructed:

```
func store := {.;};
func _setx := {.;};
func getx := {.;};

{
	var x := 0;

	func _setx : v = {
	    var x = {var v;};
	};

	func getx = {var x;};

	func ! store : u = {
        func _setx : {var {var u;};};
	};
};

# x remains unaccessible here

var k := 10;

func store_ptr : k; # sets x to the value of k
print {func getx;} "\n"; # access 10

var k = 5;

func store : k;
print {func getx;} "\n"; # access 5
```

## `.`

### Usage

```
. [...];
```

Executes the block(s) ignoring their return(s).

### Examples

```
. {func f;};
```

## `string`

### Usage

```
string [...];
```

Transforms parameters into strings, as long as they are compatible (for example, not audio, not functions), and concatenates if there are multiple parameters.

### Examples

```
string {func f;};
string whatever;
```

## `if`

### Usage

```
if a {...}
elif b {...}
else {...};
```

Executes a block if the value is not null (None), with support to `elif` and `else`.

### Examples

```
var x := 10;
if {var x;} {print "x is not null\n";}
else {print "x is null\n";};
```

## `switch`

### Usage

```
switch a
case b {...}
default {...};
```

Switches to the block that matches a value.

### Examples

```
var t := 4;

switch {var t;}
case "!" {print "!!!\n";}
case "?" {print "???\n";}
default {print "other\n";};
```

## `cmp`

### Usage

```
cmp a operation b;
```

Compares two values based on an operation.

Supported operations are: `>`, `>=`, `<`, `<=`, `==`, `!=`.

Note that only `==` and `!=` support string comparations, since the greater than and lesser than operations are not well defined for strings.

### Examples

```
var x := 5;
if {cmp {var x;} > 10;} {
	print "x is greater than 10;
};
```

## `op`

### Usage

```
op operation value; # 1
op a operation b; # 2
```

(1) Evaluates an operation with a single value. Supports `not`, `abs`, `log`, `~`. `log` is base e=2.73...

(2) Evaluates an operation with two values. Supports `+`, `-`, `*`, `**` (exponentiation), `/`, `//` (integer division), `%` (programming module), `mod` (mathematics module), `&`, `|`, `^`, `and`, `or`, `xor`, `nand`, `nor`, `xnor`, `<<`, `>>`.

### Examples

```
var x := 10;
var x = {op {var x;} * 2;};
var x = {op {var x;} - 1;};
```

## `while`

### Usage

```
while {...} {...};
```

Continues to execute the second block if the first evaluates to a non-null value. Does **NOT** return anything.

### Examples

```
var x := 10;

while {cmp x != 0;}{
	var x = {op {var x;} - 1;};
};
```

## `strop`

### Usage

```
strop contains a b; # 1
strop slice a i j; # 2
strop find a b; # 3
strop replace a b c; # 4
strop strip a; # 5
strop size a; # 6
```

Collective for string operations.

(1) Returns `"true"` if `b` is a substring of `a`.
(2) Returns a substring starting at index i (inclusive) and ending at j (exclusive).
(3) Returns the index of `b` as a substring of `a`, null if it isn't a substring.
(4) Replaces all occurences of `b` into `c` inside `a`.
(5) Removes trailing whitespace of a string.
(6) Returns the size (length) of the string `a`.

### Examples

```
var h := "hello planet";
var h = {strop replace {var h;} "planet" "world";};
```

## `ampfx`

### Usage

```
ampfx t0 : v0 -> t1 : v1 | audio;
```

Applies a amplitude effect on an audio.

The effect to be applied is according to:

- Before t0, multiply by v0.
- Between t0 and t1, interpolate between v0 and v1.
- After t1, multiply by v1.

Time is in proportion of the duration of the audio (0 to 1).

### Examples

```
ampfx 0 : 0 -> 1 : 0.8 | {C 10;};
```

## `gliss`

### Usage

```
gliss a b [duration];
```

Reads from variables: `duration`, `octave`, `instrument`, `bpm`, `intensity`.

Creates a glissando based on two note names and an optional duration.

### Examples

```
gliss C D 3;
```