analyst_instructions = """
You are tasked with creating a set of AI analyst personas. Follow these instructions carefully:

1. First, review the research topic:
{topic}

2. Examine any editorial feedback that has been optionally provided to guide creation of the analysts:
{human_analyst_feedback}

3. Determine the most interesting themes based upon the topic and the feedback above.

4. Pick the top {max_analysts} themes, one analyst per theme.
"""
