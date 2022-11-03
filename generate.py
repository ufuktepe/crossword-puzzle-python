import sys

from collections import deque

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var, words in self.domains.items():
            self.domains[var] = {w for w in words if len(w) == var.length}

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        # Get the overlapping indices
        i, j = self.crossword.overlaps[x, y]
        revised = False

        # Compare the index i of each word in x's domain to the index j of each
        # word in y's domain
        for word in list(self.domains[x]):
            conflict = True
            for other_word in self.domains[y]:

                # If there is a match then there is no conflict
                if word[i] == other_word[j]:
                    conflict = False
                    break

            if conflict:
                self.domains[x].remove(word)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs:
            queue = deque(arcs)
        else:
            # If arcs is None, get all intersecting arcs
            queue = deque([k for k, v in self.crossword.overlaps.items()
                           if v is not None])

        # Loop until the queue is empty or x's domain is empty
        while queue:
            x, y = queue.popleft()
            if self.revise(x, y):

                # If x's domain is empty, there is no solution
                if not self.domains[x]:
                    return False

                # Add arcs between x's neighbors (except y) and x to the queue
                for z in self.crossword.neighbors(x) - {y}:
                    queue.append((z, x))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return len(self.domains) == len(assignment)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check if all values are distinct
        if len(set(assignment.values())) != len(assignment):
            return False

        for x, word in assignment.items():

            # Check the length
            if x.length != len(word):
                return False

            # Check for conflicts
            for y in self.crossword.neighbors(x):
                i, j = self.crossword.overlaps[x, y]
                if y in assignment and assignment[y][j] != word[i]:
                    return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        # Dictionary to count the number of values that each word rules out
        counter = {word: 0 for word in self.domains[var]}

        for word in self.domains[var]:

            # iterate over each neighbor that doesn't have an assigned value
            for neighbor in self.crossword.neighbors(var) - set(assignment):
                i, j = self.crossword.overlaps[var, neighbor]

                for other_word in self.domains[neighbor]:
                    # Check if the words are the same or if there is a conflict
                    if word == other_word or word[i] != other_word[j]:
                        counter[word] += 1

        # Sort the dictionary by value and return the list of words
        sorted_counter = sorted(counter.items(), key=lambda item: item[1])
        return [item[0] for item in sorted_counter]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # List of unassigned variables
        remaining = [var for var in self.crossword.variables - set(assignment)]

        # Sort by fewest number of values in domain and highest degree
        remaining.sort(key=lambda var: (len(self.domains[var]),
                                        -len(self.crossword.neighbors(var))))
        return remaining[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # Return the assignment if it is complete
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)

        for word in self.order_domain_values(var, assignment):
            assignment[var] = word

            # Check for consistency
            if self.consistent(assignment):

                # Maintain arc consistency
                self.ac3([(neighbor, var) for neighbor in
                          self.crossword.neighbors(var)])

                result = self.backtrack(assignment)
                if result:
                    return result

            del assignment[var]

        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
