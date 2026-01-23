Book Writer Current setup: 
1. Run Ollama in the background. Program uses Llama3.1:8b since it can run lightweight on an old Mac laptop and also is the target of copyright infringement litigation against Meta. This project substantiates a claim made in summary judgement that I was initially skeptical of, which Judge Chhabria also said was insufficiently proved by plaintiffs.
> "This case, unlike any of those cases, involves a technology that can generate literally millions of secondary works, with a miniscule fraction of the time and creativity used to create the original works it was trained on." --Judge Chhabria, 23-cv-03417-VC / Dkt. 598.
   ```
   pip install ollama
   ollama pull llama3.1:8b
   [Separate window:] ollama serve
   ```
2. Navigate to folder, clear output folder contents, install dependencies, run program
   ```
   python -m pip install ollama pandas
   python main.py
   ```

Current architecture:
1. Input book prompt
2. Outline Model receives book prompt
    - System prompt: Specialized outline instructions
    - User prompt: user's saved input
    - Creates **book_output.md**, an outline of the form:
      ```
      # [Book Title]
      #### [Chapter number]. [Chapter name]
      - Bullet point describing what happens, what characters are involved, etc. 1
      - Bullet point describing what happens, what characters are involved, etc. 2
      ```
3. Python code splits chapters into a CSV using Regex
     - Produces chapters.csv of the form:

      | Book Title |
      |---|
      | Chapter 1: - info - info - info | 
      | Chapter 2: - info - info - info |

4. Iterate through the CSV's chapter list. Per chapter,
    1. Beats Planner makes a 'beats' plan, describing each chunk of what happens in the story and putting in parenthases what kind of writing it is, choosing from: **exposition**, **description**, **dialogue**, or **actions**.
       - System prompt: Specialized beats planning instructions
       - User prompt: Chapter plan from the chapter list.
       - Output example:
       > 1. Lyra sips her morning coffee, staring blankly at the wall as she waits for the latest batch of coordinates (exposition)
       > 2. The door to her small office creaks open, and her supervisor, Mr. Blackwood, enters with a folder full of papers (description)
    2. Split the beats into a CSV of the form:

   | Text | pin |
   |---|---|
   | Lyra sips her morning coffee, staring blankly at the wall as she waits for the latest batch of coordinates | exposition |
   | The door to her small office creaks open, and her supervisor, Mr. Blackwood, enters with a folder full of papers | description |

    3. Output the chapter beats list as chapter_n_beats.md and chapter_n_beats.csv
    4. Iterate through the beats. For each beat,
        - Run Beat Writer.
          - System prompt: Specialized instructions based on the Pin input (exposition/dialogue/actions/description).
          - Assistant history: All the prior text within the same chapter (to minimize context rot).
          - User prompt: Specialized instructions alongside the beat description.
        - Append text to chapter_n_manuscript.md, as well as the third column of chapter_n_beats.csv
    5. Append chapter text to manuscript.md






