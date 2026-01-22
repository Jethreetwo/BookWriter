import json
from pathlib import Path
from ollama import chat
import urllib.request
import csv, re
import pandas as pd

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

def get_book_prompt():
    """Collect a non-empty prompt from the user."""
    prompt = input("Book prompt: ").strip()
    return prompt

def call_ollama(prompt):
    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a professional author writing an outline for a book on this topic. Your output will be of this format:
                    # [Book Title]

                    #### [Chapter number]. [Chapter name]
                    - Bullet point describing what happens, what characters are involved, etc. 1
                    - Bullet point describing what happens, what characters are involved, etc. 2
                    - Bullet point describing what happens, what characters are involved, etc. 3

                    Repeat until the end of the book. Output nothing else. No prologue, no epilogue. Just chapters ONLY. 
                """
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response["message"]["content"]

def save_text(text, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def split_chapters(plan, path: Path) -> None:
    m = re.search(r'^\s*#\s+(.*)\s*$', plan, flags=re.M)
    title = m.group(1).strip() if m else ""
    chapters = []
    for mm in re.finditer(r'^\s*####\s+(.*)\s*$\n((?:^\s*-\s.*\n?)*)', plan, flags=re.M):
        header = mm.group(1).rstrip()
        bullets = mm.group(2).rstrip("\n")
        chapters.append((header + "\n" + bullets).strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([title])
        for c in chapters:
            w.writerow([c])

def make_beats(chapter_plan):
    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
                You are an expert novelist and outline architect. You are going to plan the described full chapter.
                - Write a chapter “event plan” as a numbered list.
                - Each line is ONE beat (a single moment, action, conversation, reveal, or short chunk of exposition).
                - At the end of EVERY line, add exactly one tag in parentheses choosing from: (exposition) (description) (actions) (dialogue)
                - Aim for 30 beats, with 40% action, 30% dialogue, 15% description, 15% exposition
                IMPORTANT: Output ONLY the numbered list with tags on each line, nothing else. Format as such: "1. Beat description (type)"
                """
            },
            {
                "role": "user",
                "content": chapter_plan
            }
        ]
    )
    return response["message"]["content"]

def write_beat(beat_text, beat_type, prior_context):
    # System prompts for each beat type
    if(beat_type == "exposition"):
        beat_instructions = """Write concise narrative exposition that orients the reader: essential context, stakes, and causal background. Weave facts into scene/voice; avoid info-dumps, summaries of unneeded history, and author lecturing. Reveal only what this moment needs; imply more than you explain."""
    if(beat_type == "dialogue"):
        beat_instructions = """Write dialogue-driven beats: character voice, subtext, and conflict. Keep lines natural and purposeful; vary rhythm; use interruptions, implication, and specificity. Minimal dialogue tags and no on-the-nose exposition; let what’s unsaid carry meaning."""
    if(beat_type == "description"):
        beat_instructions = """Write vivid, selective sensory description (concrete, specific details) filtered through the POV’s attitude. Prioritize the 2–5 most telling details; use metaphor sparingly and precisely. Avoid cataloging, purple prose, and generic adjectives; make setting/mood do narrative work."""
    if(beat_type == "actions"):
        beat_instructions = """Write clear, cinematic action in tight cause-and-effect. Use strong verbs, concrete physicality, and readable spatial logic; keep sentences lean to control pace. Show reactions and consequences; avoid long introspection, explanation, and vague choreography."""
    
    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"You are currently writing {beat_type} within a chapter of a novel. As a good writer of {beat_type}, you should: " + beat_instructions
            },
            {
                "role": "assistant",
                "content": prior_context
            },
            {
                "role": "user",
                "content": f"Continue what you had written before by writing {beat_type}, noting what you have written already and being careful NOT to re-describe anything or be in any way repetitive to previous content. Write in past tense. Do NOT use ANY dashes, en dashes, em dashes, colons, or semicolons. Do not start paragraphs with 'As', and use varied sentence structure. IMPORTANT. THIS IS YOUR TOPIC: {beat_text}"
            }
        ]
    )
    return response["message"]["content"]

def write_chapter(chapter_plan):
    # Pick up chapter_plan as "Chapter 1. Text", save to CSV
    beats_list = make_beats(chapter_plan)
    # Turn beats into dataframe
    df = pd.DataFrame(
        re.findall(r'^\s*\d+\.\s*(.*)\s*\(([^()]*)\)\s*\.?\s*$', beats_list, flags=re.M),
        columns=["Text", "pin"]
        )
    # Which chapter is this?
    n = (re.search(r'\bChapter\s+(\d+)\b', chapter_plan) or re.search(r'\b(\d+)\b', chapter_plan)).group(1)
    print(f"\nFinished making beats for Chapter {n}")

    # Save to md and CSV
    chapter_beats_out_path_as_md = Path("output") / f"chapter_{n}_beats.md"
    chapter_beats_out_path_as_csv = Path("output") / f"chapter_{n}_beats.csv"
    save_text(beats_list, chapter_beats_out_path_as_md)
    df.to_csv(chapter_beats_out_path_as_csv, index=False)
    print(f"\nSaved Chapter Beats for Chapter {n} to md and CSV")
    
    # Iterate over the CSV, write to the third column of the CSV every time a beat finishes 
    # for beat in nrow(df):
    #   beat_text = write_beat(df[beat], df[beat type], df[prior context])
    #   # Save Beat to CSV
    #   Placeholder code to submit to CSV column 3
    # Concat CSV column 3 to chapter_text
    # Save chapter_text as manuscript_chapter_{n}_text.md

    num_of_beats = range(1, len(df)+1)
    df["written_output"] = ""
    chapter_manuscript_out_path = Path("output") / f"chapter_{n}_manuscript.md"
    save_text("",chapter_manuscript_out_path)
    for beat in num_of_beats:
        # Extract context if existent: this code takes the last written beat: 
        # i = beat - 2
        # context = df.iloc[i, 2] if 0 <= i < len(df) else ""
        with open(chapter_manuscript_out_path, "r", encoding="utf-8") as f:
            context: str = f.read()
        beat_output = write_beat(df.iloc[beat-1,0], df.iloc[beat-1,1], context)
        df.iat[beat-1,2] = beat_output
        print(f"\nWrote Beat {beat} for Chapter {n} to dataframe")
        with open(chapter_manuscript_out_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + beat_output)
        print(f"\nWrote Beat {beat} to Chapter {n} manuscript")

    chapter_beats_out_path_as_csv_with_outputs = Path("output") / f"chapter_{n}_beats_written.csv"
    df.to_csv(chapter_beats_out_path_as_csv_with_outputs, index=False)
    print(f"\nSaved Chapter Beats with writing for Chapter {n} to CSV")

    with open(chapter_manuscript_out_path, "r", encoding="utf-8") as f:
        chapter_text = f.read()
    return chapter_text

    # Pseudocode solution: 
    # 1. Chat divides up the chapter into many beats
    # 2. Parse the beats text into a csv - one column for the beat type
    # 3. Iterate over the CSV to write. 
    #       - 4 different system prompts, plug in the appropriate skill per beat type
    #       - Give the immediately preceeding Beat output as context in the user prompt
    #       - Plug in the Beat text as the user prompt with "continue this chapter by writing out this story beat that follows it: "
    # 4. Put the written Beat in a .md file for the chapter
    # 5. Concat all the CSV 3rd columns and return as a string

def main() -> None:
    book_prompt = get_book_prompt()
    print(f"\n{MODEL} is cooking")

    result = call_ollama(book_prompt)
    print(f"\n{MODEL} has cooked")

    plan_out_path = Path("output") / "book_output.md"
    save_text(result, plan_out_path)
    print(f"\nWrote output to: {plan_out_path}")

    chapters_out_path = Path("output") / "chapters.csv"
    split_chapters(result, chapters_out_path)
    print(f"\nWrote chapters CSV to: {chapters_out_path}")
    
    chapterlist = pd.read_csv(chapters_out_path)
    num_chapters = range(1,len(chapterlist)+1)
    manuscript_out_path = Path("output") / "manuscript.md"
    manuscript = ""
    for chapter in num_chapters:
        chapter_text = write_chapter(chapterlist.iloc[chapter-1, 0])
        current_chapter_name = re.search(r"\.\s*([\s\S]*?)\s*-", chapterlist.iloc[chapter-1, 0]).group(1).strip()
        manuscript += f"\n\n#### Chapter {chapter}: {current_chapter_name}\n{chapter_text}\n"
        print(f"\nWrote chapter {chapter}")
    manuscript_out_path.write_text(manuscript, encoding="utf-8")
    print(f"\nWrote Manuscript to: {manuscript_out_path}")

if __name__ == "__main__":
    main()
    '''write_chapter("""
                    Chapter 1. The Great Pick-Off
                    - Introduce protagonist, Jack ""The Whittler"" Wilson, a struggling guitar pick artisan with a dream to create the ultimate pick.
                    - Describe the prestigious Golden Pick Award and its esteemed judges, known for their exacting standards.
                    - Show Jack's workshop, where he meticulously crafts each pick by hand.
                  """)'''