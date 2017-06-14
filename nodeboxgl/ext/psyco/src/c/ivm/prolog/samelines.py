#
# Search for identical lines in stdin. Line starting with "<number>*"
# are assumed to be repeated that number of times.
# stdout report is formatted according to sys.argv[1].
#
import sys, re

re1 = re.compile(r"([0-9]+)[*](.*)")

def samelines(infile, outfile, format, verbose=1, minimum=2):
    lines = {}
    total = 0
    try:
        for line in infile:
            verbose -= 1
            if not verbose:
                if total:
                    print >> sys.stderr, '%d lines, %d without duplicates...' % (
                        total, len(lines))
                total += 5000
                verbose = 5000
            if line.endswith('\n'):
                line = line[:-1]
            match = re1.match(line)
            if match:
                count = int(match.group(1))
                line = match.group(2)
            else:
                count = 1
            lines[line] = lines.get(line, 0) + count
    finally:
        for line, count in lines.iteritems():
            if count >= minimum:
                print >> outfile, format % (line, count)

if __name__ == '__main__':
    format = sys.argv[1]
    samelines(sys.stdin, sys.stdout, format)
