# Full and Detailed Instructions: Assignment 03 - Mass Production of AI Agents and LaTeX Document Generation

This document is intended to serve as a Prompt / background material for a language model (like Claude) so it understands the full scope, requirements, and architecture needed to complete Assignment 03 in the CrewAI and LaTeX project. Do not omit any detail from this document when planning and developing the solution.

## 1. Main Goal of the Assignment
Building an autonomous agent crew using the **CrewAI** library that will write a professional article or book on a topic of your choice, and output the final product as a professional and formatted PDF document using **LaTeX**.

---

## 2. Agent Architecture & Workflow
The system must consist of a Crew of multiple agents, working in a Sequential or Hierarchical workflow configuration, where the output of one agent serves as the Context for the next agent.

You must implement at least the following roles (as reflected in the pseudocode example in the source document):

1. **Researcher Agent:**
   * **Role:** Conduct research and gather accurate data and key facts.
   * **Tools:** It is mandatory to connect this agent to the internet using a search tool (e.g., `SerperDevTool` for Google search).
2. **Writer Agent:**
   * **Role:** Turn the raw research materials into a structured, readable, and clear article.
   * **Context:** Receives the facts and sources from the Researcher agent. **Do not connect this agent directly to an internet search tool.**
3. **Reviewer / Quality Control Agent:**
   * **Role:** Check factual accuracy and improve text clarity without changing the original meaning.
4. **LaTeX Generation Agent:**
   * **Role:** Convert the final, approved text into valid LaTeX code ready for compilation.
   * *Process Note:* It is highly recommended that the crew first generates the output in Markdown format (for quick and easy review), and only after the content is approved and perfect, this agent will convert it to a `.tex` format.

---

## 3. Content and Structure Requirements for the Final PDF Document
The final output must meet the following strict requirements:

* **Document Scope:** Approximately 15 pages. (Note: Writing in Hebrew is considered more challenging and is therefore more highly evaluated).
* **Cover Sheet:** Must include: Article/Book Topic, Author's Name, Date, Course Name, and Lecturer's Name.
* **Basic Structure:** The document must include:
  * Table of Contents.
  * Clear division into chapters.
  * Headers & Footers.
* **Visual and Content Elements - Must include at least one of each type:**
  1. One image.
  2. One graph (generated programmatically using Python code, not copied as a static output).
  3. One table.
  4. One mathematical formula. *Emphasis for the LaTeX Agent:* Must produce "fancy formulas" using LaTeX math packages and not as plain text.
* **Language Integration (BiDi - Bidirectional text):** 
  Must include at least one chapter demonstrating proper and correct transitions between Right-to-Left (Hebrew) and Left-to-Right (English). Sometimes the model tends to output formulas as plain text due to directionality confusion - it must be instructed to fix this if necessary.
* **References and Bibliography:**
  The document must end with a bibliography list, and the text itself must include linked (clickable) citations pointing to this list.

---

## 4. Technical Workspace and LaTeX Compilation Requirements
The document explicitly states which tools are recommended to overcome the compilation challenge, especially when dealing with Hebrew:

* **Compilation Environment / Compiler:** Recommended to use **MiKTeX**.
* **Compilation Engine for Hebrew:** Use **LuaLaTeX** (recommended due to excellent Hebrew support) or alternatively **XeLaTeX**.
* **Bibliography Management:** Create `.bib` files, and use the **BibTeX** or **biber** compiler (which come with MiKTeX).
* **Compilation Process (Strict Warning):** When there are `.tex` and `.bib` files together, you must run about **4 consecutive compilations** to ensure all references and citations are fully updated. (If clicking a reference in the document does not jump to the citation in the bibliography - it means a compilation is missing).
* **Graphics and Schematics:** Use the **TikZ** library in LaTeX for creating block diagrams if needed.

---

## 5. Assignment Evaluation Criteria (What to look out for)
The evaluation of the assignment will primarily be **technical (on the wrapper/envelope)** and not necessarily on the factual correctness of the article. Therefore, ensure that the agents' code produces an output that meets the following metrics:
* Links and citations are connected, exist, and are clickable.
* Text directionality (BiDi - Hebrew and English) is correct and not corrupted.
* Tables do not exceed the page margins.
* Formulas are compiled properly ("fancy formulas").
