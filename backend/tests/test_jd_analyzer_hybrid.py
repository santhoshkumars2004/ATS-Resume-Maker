import asyncio

from backend.agents.jd_analyzer import analyze_jd
from backend.llm.base import LLMProvider


class IncompleteJDProvider(LLMProvider):
    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ):
        return {
            "job_title": "",
            "company": "",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "keywords": ["Build"],
            "experience_years": 0,
            "tech_stack": ["Python"],
            "responsibilities": [],
            "education": "",
            "job_type": "",
            "location": "",
        }

    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        return ""


def test_analyze_jd_hybridizes_llm_output_with_raw_jd():
    job_description = """
Job Title: Software Engineer - Product Development
Minimum Year of experience: 0-2 Years
Qualification: BE/ME/M. Tech in IT, Computer Science or a related field
Programming / Technical Skills:
Solid proficiency in Python with a strong understanding of Object-Oriented Programming principles.
Practical experience building RESTful APIs using Node.js.
Hands-on exposure to React.js for building UI/dashboard components.
Working knowledge of AWS services (Lambda, EC2, S3) and cloud deployment fundamentals.
Exposure to Generative AI concepts with experience implementing Proof of Concepts (PoCs).
Working understanding data integration and consumption from enterprise data platforms (e.g., Snowflake).

Major tasks:
Contribute to the development and maintenance of RESTful APIs and backend services using Node.js and Python.
Support implementation of data pipelines for telemetry validation and ingestion.
Assist in cloud-based deployments and testing of services on AWS.
"""

    analysis = asyncio.run(analyze_jd(IncompleteJDProvider(), job_description, "Siemens"))

    assert analysis.company == "Siemens"
    assert analysis.job_title == "Software Engineer - Product Development"
    assert analysis.experience_years == 0
    assert "Python" in analysis.required_skills
    assert "Object-Oriented Programming" in analysis.required_skills
    assert "Node.js" in analysis.required_skills
    assert "React.js" in analysis.required_skills
    assert "AWS" in analysis.tech_stack
    assert "AWS Lambda" in analysis.tech_stack
    assert "Snowflake" in analysis.tech_stack
    assert "Generative AI" in analysis.keywords
    assert any("RESTful APIs" in responsibility for responsibility in analysis.responsibilities)
