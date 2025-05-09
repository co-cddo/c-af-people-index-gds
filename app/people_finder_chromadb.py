import json
import os

import boto3
import pandas as pd
from chromadb import Client, Settings
from chromadb.utils import embedding_functions


class PeopleFinder:
    def __init__(self, csv_path: str, persist_dir: str = "chroma_db"):
        self.csv_path = csv_path
        self.persist_dir = persist_dir

        # Initialize Chroma client with persistence
        self.chroma_client = Client(
            Settings(persist_directory=persist_dir, anonymized_telemetry=False)
        )

        # Initialize embedding function (using the same model as before for consistency)
        self.embedding_function = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="people_profiles", embedding_function=self.embedding_function
        )

        # Load and process profiles
        self.load_profiles()

        # Start bedrock runtime associated with docker image profile
        self.bedrock = boto3.client(
            service_name="bedrock-runtime", region_name="us-east-1"
        )

    # Users are I imagine going to want to see their profile and amend rather than
    # us managing it centrally
    def load_profiles(self):
        if os.path.exists(self.csv_path):
            self.profiles_df = pd.read_csv(self.csv_path)
            self._update_vector_store()
        else:
            self.profiles_df = pd.DataFrame(
                columns=[
                    "name",
                    "email",
                    "job_title",
                    "grade",
                    "location",
                    "department",
                    "skills",
                    "help",
                ]
            )
            self.profiles_df.to_csv(self.csv_path, index=False)

    def _update_vector_store(self):
        try:
            existing_ids = self.collection.get()["ids"]

            # Just need this to run for mvp so it's running based on the csv file for now.
            if existing_ids:
                self.collection.delete(ids=existing_ids)

            # Add all profiles to Chroma
            documents = []
            ids = []
            metadatas = []

            for idx, row in self.profiles_df.iterrows():
                # If some data is missing because of an incomplete profile, don't show NaNs
                row = row.fillna("")

                text = f"""
                Name: {row["name"]}
                Email: {row["email"]}
                Title: {row["job_title"]}
                Grade: {row["grade"]}
                Location: {row["location"]}
                Department: {row["department"]}
                Skills: {row["skills"]}
                Help: {row["help"]}
                """.strip()

                documents.append(text)
                ids.append(row["email"])  # email should be the unique identifier
                metadatas.append({"name": row["name"], "email": row["email"]})

            if documents:
                self.collection.add(documents=documents, ids=ids, metadatas=metadatas)
        except Exception as e:
            print(f"Error updating vector store: {e}")

    # Something to add a new person who has access or update their information in the store
    def add_or_update_profile(
        self,
        name: str,
        email: str,
        job_title: str,
        grade: str,
        location: str,
        department: str,
        skills: str,
        help: str,
    ) -> str:
        # Email is the unique ID so without it, stop the user updating stuff that exists
        if not email or not email.strip():
            return "Error: Email is required"

        email = email.strip().lower()
        existing_profile_mask = self.profiles_df["email"] == email

        if existing_profile_mask.any():
            existing_profile = self.profiles_df.loc[existing_profile_mask].iloc[0]

            # Assume user doesn't give all new data in one go, use existing data if available to update record alongside new data
            new_profile_data = {
                "name": (
                    name.strip() if name and name.strip() else existing_profile["name"]
                ),
                "email": email,
                "job_title": (
                    job_title.strip()
                    if job_title and job_title.strip()
                    else existing_profile["job_title"]
                ),
                "grade": (
                    grade.strip()
                    if grade and grade.strip()
                    else existing_profile["grade"]
                ),
                "location": (
                    location.strip()
                    if location and location.strip()
                    else existing_profile["location"]
                ),
                "department": (
                    department.strip()
                    if department and department.strip()
                    else existing_profile["department"]
                ),
                "skills": (
                    skills.strip()
                    if skills and skills.strip()
                    else existing_profile["skills"]
                ),
                "help": (
                    help.strip()
                    if help and help.strip()
                    else existing_profile["help"]
                ),
            }

            idx = self.profiles_df.index[existing_profile_mask][0]
            for column, value in new_profile_data.items():
                self.profiles_df.at[idx, column] = value
            message = f"Profile updated for {new_profile_data['name']} ({email})"

        else:
            # For new profiles, there needs to be a name at minimum alongside email
            if not name or not name.strip():
                return "Error: Name is required for new profiles"

            # Create new profile
            new_profile_data = {
                "name": name.strip(),
                "email": email,
                "job_title": job_title.strip() if job_title else "",
                "grade": grade.strip() if grade else "",
                "location": location.strip() if location else "",
                "department": department.strip() if department else "",
                "skills": skills.strip() if skills else "",
                "help": help.strip() if help else "",
            }

            new_profile = pd.DataFrame([new_profile_data])
            self.profiles_df = pd.concat(
                [self.profiles_df, new_profile], ignore_index=True
            )
            message = f"New profile added for {name} ({email})"

        self.profiles_df = self.profiles_df.fillna("")

        # Save to CSV version in the back so it's persistent and update vector store
        self.profiles_df.to_csv(self.csv_path, index=False)
        self._update_vector_store()

        return message

    def query_claude(self, query: str, context: str) -> dict:
        prompt = f"""Based on the following user query and provided employee profiles, identify the most relevant people and explain why they match the requirements. 
        
        Query: {query}
        
        Relevant profiles:
        {context}
        
        Return your response as a JSON string with this structure:
        {{
            "matches": [
                {{
                    "name": "person's name",
                    "email": "person's email",
                    "relevance_explanation": "detailed explanation of why this person matches"
                }}
            ]
        }}
        
        Ensure your response contains only the JSON object - no introduction, no explanation, no additional text.
        """

        modelId = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        #modelId="us.anthropic.claude-3-5-haiku-20241022-v1:0"
        accept = "application/json"
        contentType = "application/json"
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,  # 2000 should be more than enough to set out user profile
                "temperature": 0.3,  # 0.3 because we want accuracy but not just a 1-1 return of input data
                "top_k": 250,
                "top_p": 1,
            }
        )

        response = self.bedrock.invoke_model(
            body=body, modelId=modelId, accept=accept, contentType=contentType
        )

        response_body = json.loads(response.get("body").read())
        content = response_body.get("content", [])[0].get("text", "")
        return json.loads(content)

    def search(self, query: str, top_k: int = 5) -> str:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        context = "\n\n".join(results["documents"][0])

        claude_results = self.query_claude(query, context)

        # Extract the relevant bits from the response that we want and apply minimal formatting for user-friendliness
        output = ""
        for match in claude_results["matches"]:
            output += f"### {match['name']}\n"
            output += f"### {match['email']}\n"
            output += f"{match['relevance_explanation']}\n\n"

        return output

    # So that someone (dev? admin?) can see all current profiles within the app
    def get_all_profiles(self):
        """Get all profiles from the vector store"""
        try:
            results = self.collection.get()

            print("\n=== Vector Store Contents ===")
            for i, (doc, metadata, id_) in enumerate(
                zip(results["documents"], results["metadatas"], results["ids"])
            ):
                print(f"\nDocument {i + 1} (ID: {id_}):")
                print("Metadata:", metadata)
                print("Content:", doc)
                print("-" * 50)

            return results
        except Exception as e:
            print(f"Error retrieving profiles: {e}")
            return None

    # Helper function to sense check
    def get_profile_count(self):
        """Get the number of profiles in the vector store"""
        try:
            results = self.collection.get()
            return len(results["ids"])
        except Exception as e:
            print(f"Error getting profile count: {e}")
            return 0
