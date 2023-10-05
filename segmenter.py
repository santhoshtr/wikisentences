import re
import sys
from symbols import GLOBAL_SENTENCE_TERMINATORS
from typing import List
from sentencex import segment

MIN_SENTENCE_LENGTH = 2
if __name__ == "__main__":
    language = sys.argv[1]
    for line in sys.stdin:
        if len(line.strip()) > 1:
            sentences = segment(language, line)
            for sentence in sentences:
                if len(sentence.strip()) > MIN_SENTENCE_LENGTH: # Avoid very short sentences
                    print(sentence.strip())