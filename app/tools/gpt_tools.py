"""
Tools for the agent system.
"""
from datetime import datetime
from langchain_core.tools import tool
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_core.prompts import PromptTemplate
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from app.config.chat_config import ChatConfig

class ToolManager:
    """Manager for all tools used by the agent."""
    config = ChatConfig()

    @staticmethod
    @tool
    def get_current_time() -> str:
        """Get the current time of the user"""
        now = datetime.utcnow()
        current_time = f'the current time is {now.strftime("%d-%B-%Y")}'
        return current_time
        
    @staticmethod
    @tool
    def query_database(query: str) -> str:
        """Execute a database query and return the results.
        The query should be specific about what data is needed.
        Example queries:
        - Show me top products by revenue
        - Get customer conversion rates by month
        - Calculate average order value by product category
        """
        # This is a simplified implementation - in a real system, you would:
        # 1. Parse the natural language query
        # 2. Translate to SQL or other database query language
        # 3. Execute against your actual database
        # 4. Format and return the results
        
        # For demo purposes, return sample data based on keywords in query
        if "products" in query.lower() or "revenue" in query.lower():
            return """
            | Product          | Revenue   | Units Sold |
            |------------------|-----------|------------|
            | Attribution Pro  | $125,000  | 250        |
            | Marketing Suite  | $87,500   | 350        |
            | Analytics Basic  | $45,000   | 900        |
            | Data Connector   | $32,500   | 650        |
            """
        elif "customer" in query.lower() or "conversion" in query.lower():
            return """
            | Month     | Visitors | Conversions | Rate  |
            |-----------|----------|-------------|-------|
            | January   | 25,400   | 762         | 3.0%  |
            | February  | 28,500   | 913         | 3.2%  |
            | March     | 32,100   | 1,091       | 3.4%  |
            | April     | 30,800   | 956         | 3.1%  |
            """
        elif "average" in query.lower() or "order" in query.lower():
            return """
            | Category        | Avg Order Value |
            |-----------------|-----------------|
            | Enterprise      | $3,250          |
            | Mid-market      | $1,125          |
            | Small Business  | $485            |
            """
        else:
            return "I don't have specific data for that query. Please try a more specific question about products, revenue, customers, or order values."

    @classmethod
    def configure_retriever(cls):
        """Configure and return a vector store retriever."""
        embeddings = OpenAIEmbeddings(
            model=cls.config.VECTOR_STORE_CONFIG["embedding_model"],
            dimensions=cls.config.VECTOR_STORE_CONFIG["dimensions"]
        )

        vectorstore = PineconeVectorStore(
            index_name=cls.config.VECTOR_STORE_CONFIG["index_name"],
            embedding=embeddings
        )

        retriever = vectorstore.as_retriever(
            search_type=cls.config.RETRIEVER_CONFIG["search_type"],
            search_kwargs={
                "k": cls.config.RETRIEVER_CONFIG["k"],
                "fetch_k": cls.config.RETRIEVER_CONFIG["fetch_k"],
                "lambda_mult": cls.config.RETRIEVER_CONFIG["lambda_mult"]
            }
        )
        return retriever

    @classmethod
    def get_retriever_tool(cls):
        """Create and return a retriever tool."""
        retriever = cls.configure_retriever()

        return create_retriever_tool(
            retriever,
            cls.config.RETRIEVER_TOOL_CONFIG["name"],
            cls.config.RETRIEVER_TOOL_CONFIG["description"],
            document_prompt=PromptTemplate.from_template(cls.config.DOCUMENT_PROMPT_TEMPLATE)
        )

    @classmethod
    def get_rag_tools(cls):
        """Get tools for RAG-enabled agent."""
        return [cls.get_retriever_tool(), cls.get_current_time]

    @classmethod
    def get_standard_tools(cls):
        """Get tools for standard (non-RAG) agent."""
        return [cls.get_current_time]
        
    @classmethod
    def get_database_tools(cls):
        """Get tools for database operations."""
        return [cls.query_database, cls.get_current_time]
