from typing import List


def capture_trailing_space(split_sentence: List[str]) -> List[str]:
    # add documentation in sphinx format
    """
    This function concatenates a sentence only consisting of whitespaces as
    trailing whitespaces to the previous sentence.
    :params split_sentences: The list of splitted sentence from the sentence segmenter.
    :type split_sentence: List of sentence segments

    :return: A list of :class: `str` objects
    :rtype: List[str]

    """
    final_sentences = []
    idx = 0
    num_sentences = len(split_sentence)

    if num_sentences == 1:
        return split_sentence

    while idx < num_sentences:
        current_sentence = split_sentence[idx]
        # capturing trailing spaces
        while idx + 1 < num_sentences and split_sentence[idx + 1].strip() == "":
            idx += 1
            current_sentence += split_sentence[idx]
        idx += 1
        final_sentences.append(current_sentence)
    return final_sentences
