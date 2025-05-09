import gradio as gr
from people_finder_chromadb import PeopleFinder


def search_profile_interface(finder: PeopleFinder) -> gr.Blocks:
    with gr.Blocks() as interface:
        search_input = gr.Textbox(
            label= "Search for people based on their skills, experience, and expertise.",
            lines=2,
            placeholder="Enter your search query (e.g., 'Looking for people with experience in data science and workforce analytics')",
        )
        search_button = gr.Button("Search")

        with gr.Column() as results_column:
            status_text = gr.Markdown("Ready to search...")
            search_output = gr.Markdown()

        def search_wrapper(query: str) -> tuple[str, str]:
            status = "🔄 Searching profiles..."
            try:
                result = finder.search(query)
                status = "✅ Search complete!"
            except Exception as e:
                status = f"❌ Error during search: {str(e)}"
                result = "An error occurred while searching. Please try again."
            return status, result

        search_button.click(
            fn=search_wrapper,
            inputs=[search_input],
            outputs=[status_text, search_output],
            show_progress="full",  # This will show a progress indicator
        )

        # Add in basic examples for search so people have an idea what they can ask
        gr.Examples(
            examples=[
                [
                    "I am looking for someone with expertise in style guides and accessibility"
                ],
                [
                    "I need help in healthcare analytics and data governance"
                ],
                ["I want to find someone with expertise in policy research and modelling"],
            ],
            inputs=search_input,
        )

        return interface


def manage_profile_interface(finder: PeopleFinder) -> gr.Blocks:
    with gr.Blocks() as interface:
        gr.Markdown("Add or update employee profiles")

        name_input = gr.Textbox(label="Name")
        email_input = gr.Textbox(label="Email")
        job_title_input = gr.Textbox(label="Job Title")
        department_input = gr.Textbox(label="Department")
        team_input = gr.Textbox(label="Team")
        skills_input = gr.Textbox(
            label="Skills",
            lines=3,
            placeholder="Enter skills separated by commas (e.g., Python, Data Analysis, Project Management)",
        )
        experience_input = gr.Textbox(
            label="Experience",
            lines=3,
            placeholder="Describe relevant work experience and projects",
        )

        submit_button = gr.Button("Submit Profile")
        result_output = gr.Markdown()

        submit_button.click(
            fn=finder.add_or_update_profile,
            inputs=[
                name_input,
                email_input,
                job_title_input,
                department_input,
                team_input,
                skills_input,
                experience_input,
            ],
            outputs=result_output,
        )

        # Update example profile
        # TODO: Maybe show the updated profile data instead?
        gr.Examples(
            examples=[
                [
                    "John Doe",
                    "john.doe@example.com",
                    "Senior Data Scientist",
                    "Analytics",
                    "Data Science",
                    "Python, R, Machine Learning, SQL, Data Visualization",
                    "5 years experience in workforce analytics, led multiple projects on employee retention modeling",
                ]
            ],
            inputs=[
                name_input,
                email_input,
                job_title_input,
                department_input,
                team_input,
                skills_input,
                experience_input,
            ],
        )

    return interface


def view_profile_data(finder: PeopleFinder) -> gr.Blocks:
    with gr.Blocks() as interface:
        gr.Markdown("### Current Profiles in Vector Store")

        def format_profiles_for_display():
            try:
                results = finder.collection.get()
                if not results or not results["documents"]:
                    return "No profiles found in the vector store."

                formatted_output = ""
                for i, (doc, metadata, id_) in enumerate(
                    zip(
                        results["documents"],
                        results["metadatas"],
                        results["ids"],
                    )
                ):
                    formatted_output += f"### Profile {i + 1} (ID: {id_})\n"
                    if metadata is not None:
                        formatted_output += f"**Name:** {metadata.get('name', 'N/A')}\n"
                    else:
                        formatted_output += "**Name:** N/A\n"
                    formatted_output += f"**Content:**\n```\n{doc}\n```\n\n"
                    formatted_output += "---\n\n"

                return formatted_output
            except Exception as e:
                return f"Error retrieving profiles: {str(e)}"

        # Add refresh button assuming that data was updated in other manage profile tab
        refresh_button = gr.Button("Refresh Profiles")
        profiles_display = gr.Markdown()

        # Show profiles on refresh
        refresh_button.click(
            fn=format_profiles_for_display, inputs=[], outputs=profiles_display
        )

        try:
            initial_display = format_profiles_for_display()
            profiles_display.value = initial_display
        except Exception as e:
            profiles_display.value = f"Error initializing display: {str(e)}"

    return interface
