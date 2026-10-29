RESOURCE_BY_SKILL = {
    "python": ("Python Tutorial", "https://docs.python.org/3/tutorial/"),
    "html": ("MDN HTML basics", "https://developer.mozilla.org/en-US/docs/Learn/HTML"),
    "css": ("MDN CSS basics", "https://developer.mozilla.org/en-US/docs/Learn/CSS"),
    "javascript": ("MDN JavaScript guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    "sql": ("SQLBolt interactive lessons", "https://sqlbolt.com/"),
    "git": ("Git book", "https://git-scm.com/book/en/v2"),
    "react": ("React Learn", "https://react.dev/learn"),
    "linux": ("Linux Journey", "https://linuxjourney.com/"),
    "machine learning": ("Google Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course"),
    "pandas": ("Pandas getting started", "https://pandas.pydata.org/docs/getting_started/"),
    "statistics": ("Khan Academy statistics", "https://www.khanacademy.org/math/statistics-probability"),
    "testing": ("MDN testing overview", "https://developer.mozilla.org/en-US/docs/Learn/Tools_and_testing"),
    "networking": ("Cisco Networking Basics", "https://www.netacad.com/courses/networking-basics"),
    "cloud": ("AWS Cloud Practitioner Essentials", "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/"),
    "excel": ("Microsoft Excel help & learning", "https://support.microsoft.com/excel"),
    "data visualization": ("Datawrapper Academy", "https://academy.datawrapper.de/"),
    "problem solving": ("freeCodeCamp", "https://www.freecodecamp.org/learn/"),
    "communication": ("British Council LearnEnglish", "https://learnenglish.britishcouncil.org/"),
}

EXERCISE_BY_SKILL = {
    "python": "Write a command-line program that reads a CSV file and summarizes its rows.",
    "html": "Build an accessible profile page with headings, links, and a contact section.",
    "css": "Make a one-page portfolio responsive at mobile and desktop widths.",
    "javascript": "Create a small form that validates input and updates the page without reloading.",
    "sql": "Design a small database and write queries that filter, join, and group its records.",
    "git": "Create a repository, make focused commits, and document the project in a README.",
    "react": "Build a small component-based app with a form and a filtered list.",
    "linux": "Practice navigating files and managing processes in a local or browser-based Linux shell.",
    "machine learning": "Train and evaluate a simple model on a public learning dataset.",
    "pandas": "Load a public CSV, clean missing values, and produce a short summary.",
    "statistics": "Summarize a small dataset with descriptive statistics and explain the results.",
    "testing": "Write tests for valid, invalid, and boundary inputs in a small project.",
    "networking": "Diagram a simple web request from a browser to a server and explain each step.",
    "cloud": "Deploy a small static or demo app by following an official cloud getting-started guide.",
    "excel": "Create a spreadsheet with formulas, filters, and a clearly labeled chart.",
    "data visualization": "Create a chart from a public dataset and write two evidence-based observations.",
}


def build_learning_plan(missing_skills):
    phases = [
        ("Week 1: Foundations", "Study the basics and take concise notes."),
        ("Week 2: Core skills", "Complete guided exercises and practice examples."),
        ("Week 3: Practical implementation", "Apply the skill in a small, testable project."),
        ("Week 4: Portfolio and revision", "Document the work, review gaps, and prepare to explain it."),
    ]
    skills = missing_skills[:4]
    plan = []
    for index, (week, activity) in enumerate(phases):
        if not skills:
            plan.append({
                "week": week,
                "tasks": [{
                    "title": f"{week.split(':', 1)[0]} - Review a demonstrated skill and document a project example.",
                    "skill": "Portfolio review",
                    "why": "No high-priority gap was identified from the available resume text.",
                    "activity": activity,
                    "exercise": "Choose one project you completed and write down your own contribution and tools.",
                    "estimate": "2–4 hours (estimate)",
                    "resource_name": "freeCodeCamp",
                    "resource_url": "https://www.freecodecamp.org/learn/",
                    "goal": "Write one accurate project example describing your own contribution.",
                }],
            })
            continue
        skill = skills[min(index, len(skills) - 1)]
        resource_name, resource_url = RESOURCE_BY_SKILL.get(
            skill, ("freeCodeCamp", "https://www.freecodecamp.org/learn/")
        )
        plan.append({
            "week": week,
            "tasks": [{
                "title": f"{week.split(':', 1)[0]} - Build your {skill.title()} foundation",
                "skill": skill.title(),
                "why": f"{skill.title()} appears as a gap in the selected role comparison; this does not prove you lack the skill.",
                "activity": activity,
                "exercise": EXERCISE_BY_SKILL.get(
                    skill, f"Complete a small, testable exercise that demonstrates {skill.title()}."
                ),
                "estimate": "3–5 hours (estimate)",
                "resource_name": resource_name,
                "resource_url": resource_url,
                "goal": f"Complete one small exercise using {skill.title()} and save evidence of your work.",
            }],
        })
    return plan
