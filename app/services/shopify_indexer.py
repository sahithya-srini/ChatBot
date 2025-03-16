#!/usr/bin/env python
"""
Shopify Indexer Module

This module provides functionality to fetch content from Shopify (products and blogs) 
and index it to a vector database (Pinecone) for RAG applications.
"""

import os
import json
import logging
import requests
import time
from typing import List, Dict, Any, Tuple, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.docstore.document import Document
from pinecone import Pinecone, ServerlessSpec
import markdownify as md

from app.config.chat_config import ChatConfig
from app.utils.logging_utils import get_logger


class ShopifyIndexer:
    """
    Shopify content indexer for RAG applications.
    
    This class fetches content from a Shopify store (blogs and products) and
    indexes it to a Pinecone vector database for retrieval-augmented generation.
    """
    
    def __init__(self, config: ChatConfig = None):
        """
        Initialize the ShopifyIndexer with configuration.
        
        Args:
            config: Configuration object with Shopify and Pinecone parameters
        """
        self.config = config or ChatConfig()
        self.logger = get_logger(__name__)
        
        # API base URLs
        self.shopify_admin_api_base = f"https://{self.config.SHOPIFY_SHOP_DOMAIN}/admin/api/{self.config.SHOPIFY_API_VERSION}"
        
        # logging
        self.logger.info(f"ShopifyIndexer initialized with shop domain: {self.config.SHOPIFY_SHOP_DOMAIN}")
        
    def get_blogs(self) -> List[Dict[str, Any]]:
        """
        Get all blogs from Shopify store.
        
        Returns:
            List of blog objects containing id, handle, title, and updated_at
        """
        try:
            url = f"{self.shopify_admin_api_base}/blogs.json"
            params = {
                'fields': 'id,updated_at,handle,title',
                'limit': self.config.BLOG_FETCH_LIMIT
            }
            headers = {
                'X-Shopify-Access-Token': self.config.SHOPIFY_API_KEY
            }
            
            response = requests.get(url=url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = json.loads(response.content)
                blogs = data.get('blogs', [])
                self.logger.info(f"Retrieved {len(blogs)} blogs from Shopify")
                return blogs
            else:
                self.logger.error(f"Failed to get blogs: Status code {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving blogs: {str(e)}")
            return []
    
    def get_articles(self, blog_id: int) -> List[Dict[str, Any]]:
        """
        Get all articles for a specific blog.
        
        Args:
            blog_id: The Shopify blog ID
            
        Returns:
            List of article objects
        """
        try:
            url = f"{self.shopify_admin_api_base}/blogs/{blog_id}/articles.json"
            params = {
                'status': 'active',
                'published_status': 'published',
                'fields': 'id,blog_id,updated_at,title,body_html,handle,author',
                'limit': self.config.ARTICLE_FETCH_LIMIT
            }
            headers = {
                'X-Shopify-Access-Token': self.config.SHOPIFY_API_KEY
            }
            
            response = requests.get(url=url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = json.loads(response.content)
                articles = data.get('articles', [])
                self.logger.info(f"Retrieved {len(articles)} articles for blog ID {blog_id}")
                return articles
            else:
                self.logger.error(f"Failed to get articles: Status code {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving articles: {str(e)}")
            return []
    
    def get_products(self) -> List[Dict[str, Any]]:
        """
        Get all products from Shopify store.
        
        Returns:
            List of product objects
        """
        try:
            url = f"{self.shopify_admin_api_base}/products.json"
            params = {
                'status': 'active',
                'published_status': 'published',
                'fields': 'id,updated_at,title,body_html,handle',
                'presentment_currencies': 'USD',
                'limit': self.config.PRODUCT_FETCH_LIMIT
            }
            headers = {
                'X-Shopify-Access-Token': self.config.SHOPIFY_API_KEY
            }
            
            response = requests.get(url=url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = json.loads(response.content)
                products = data.get('products', [])
                self.logger.info(f"Retrieved {len(products)} products from Shopify")
                return products
            else:
                self.logger.error(f"Failed to get products: Status code {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving products: {str(e)}")
            return []
    
    def html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to markdown for better chunking and indexing.
        
        Args:
            html_content: HTML content to convert
            
        Returns:
            Markdown string
        """
        try:
            # Convert HTML to markdown
            markdown_content = md(html_content)
            
            # If configured, summarize long content
            if self.config.SUMMARIZE_CONTENT and len(markdown_content) > self.config.SUMMARIZE_THRESHOLD:
                # For this implementation, we're just returning as-is
                # You could add a summarization step here using OpenAI or another tool
                pass
                
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Error converting HTML to markdown: {str(e)}")
            # Return original content if conversion fails
            return html_content
    
    def prepare_blog_articles(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Prepare blog articles for indexing.
        
        Returns:
            Tuple of (blog_records, article_records)
        """
        blogs = self.get_blogs()
        all_blog_records = []
        all_article_records = []
        
        for blog in blogs:
            blog_id = blog.get('id')
            blog_handle = blog.get('handle')
            blog_title = blog.get('title')
            
            # Create blog record
            blog_url = f"{self.config.SHOPIFY_SITE_BASE_URL}/blogs/{blog_handle}"
            blog_record = {
                'title': blog_title,
                'url': blog_url,
                'type': 'blog'
            }
            all_blog_records.append(blog_record)
            
            # Get articles for this blog
            articles = self.get_articles(blog_id)
            
            for article in articles:
                article_handle = article.get('handle')
                article_title = article.get('title')
                article_body_html = article.get('body_html', '')
                
                # Convert HTML to markdown
                article_markdown = self.html_to_markdown(article_body_html)
                
                # Create article record
                article_url = f"{self.config.SHOPIFY_SITE_BASE_URL}/blogs/{blog_handle}/{article_handle}"
                article_record = {
                    'title': article_title,
                    'url': article_url,
                    'markdown': article_markdown,
                    'type': 'article'
                }
                all_article_records.append(article_record)
        
        self.logger.info(f"Prepared {len(all_blog_records)} blogs and {len(all_article_records)} articles")
        return all_blog_records, all_article_records
    
    def prepare_products(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Prepare products for indexing.
        
        Returns:
            Tuple of (product_records, variant_records)
        """
        products = self.get_products()
        all_product_records = []
        all_variant_records = []
        
        for product in products:
            product_handle = product.get('handle')
            product_title = product.get('title')
            product_body_html = product.get('body_html', '')
            
            # Convert HTML to markdown
            product_markdown = self.html_to_markdown(product_body_html)
            
            # Create product record
            product_url = f"{self.config.SHOPIFY_SITE_BASE_URL}/products/{product_handle}"
            product_record = {
                'title': product_title,
                'url': product_url,
                'markdown': product_markdown,
                'type': 'product'
            }
            all_product_records.append(product_record)
            
            # Future: add variant records if needed
        
        self.logger.info(f"Prepared {len(all_product_records)} products")
        return all_product_records, all_variant_records
    
    def index_to_pinecone(self, records: List[Dict[str, Any]]) -> bool:
        """
        Index content records to Pinecone vector database.
        
        Args:
            records: List of content records with title, url, and markdown
            
        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            # If no records, return success
            if not records:
                self.logger.warning("No records to index")
                return True
                
            self.logger.info(f"Indexing {len(records)} records to Pinecone index '{self.config.PINECONE_INDEX_NAME}'")
            
            # Initialize Pinecone
            pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
            
            # Check if index exists
            existing_indexes = pc.list_indexes().names()
            
            # Create index if it doesn't exist
            if self.config.PINECONE_INDEX_NAME not in existing_indexes:
                self.logger.info(f"Creating new Pinecone index: {self.config.PINECONE_INDEX_NAME}")
                
                pc.create_index(
                    name=self.config.PINECONE_INDEX_NAME,
                    dimension=self.config.PINECONE_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=self.config.PINECONE_CLOUD,
                        region=self.config.PINECONE_REGION
                    )
                )
                
                # Wait for index to initialize
                self.logger.info("Waiting for index to initialize...")
                time.sleep(10)
            else:
                self.logger.info(f"Using existing Pinecone index: {self.config.PINECONE_INDEX_NAME}")
            
            # Prepare documents
            docs = []
            for i, record in enumerate(records):
                # Split content into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.config.CHUNK_SIZE,
                    chunk_overlap=self.config.CHUNK_OVERLAP
                )
                
                # Create document chunks
                chunks = text_splitter.split_text(record['markdown'])
                
                # Create documents with metadata
                for j, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "title": record['title'],
                            "url": record['url'],
                            "chunk": j,
                            "source": f"{record.get('type', 'content')}"
                        }
                    )
                    docs.append(doc)
            
            # Initialize embeddings
            embeddings = OpenAIEmbeddings(
                api_key=self.config.OPENAI_API_KEY,
                model=self.config.OPENAI_EMBEDDING_MODEL,
                dimensions=self.config.PINECONE_DIMENSION
            )
            
            # Index documents
            self.logger.info(f"Indexing {len(docs)} document chunks to Pinecone...")
            
            vector_store = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=embeddings,
                index_name=self.config.PINECONE_INDEX_NAME,
                pinecone_api_key=self.config.PINECONE_API_KEY
            )
            
            self.logger.info("Indexing completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error indexing to Pinecone: {str(e)}")
            return False
    
    def index_all_content(self) -> bool:
        """
        Index all Shopify content (blogs, articles, products) to Pinecone.
        
        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            self.logger.info("Starting full content indexing...")
            
            # Prepare blog articles
            self.logger.info("Fetching blog articles...")
            blog_records, article_records = self.prepare_blog_articles()
            
            # Prepare products
            self.logger.info("Fetching products...")
            product_records, variant_records = self.prepare_products()
            
            # Combine all records
            all_records = article_records + product_records
            
            # Save intermediate files if configured
            if self.config.SAVE_INTERMEDIATE_FILES:
                os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
                
                with open(os.path.join(self.config.OUTPUT_DIR, "blogs.json"), "w") as f:
                    json.dump(blog_records, f, indent=2)
                    
                with open(os.path.join(self.config.OUTPUT_DIR, "articles.json"), "w") as f:
                    json.dump(article_records, f, indent=2)
                    
                with open(os.path.join(self.config.OUTPUT_DIR, "products.json"), "w") as f:
                    json.dump(product_records, f, indent=2)
            
            # Index to Pinecone
            self.logger.info(f"Indexing {len(all_records)} total records...")
            result = self.index_to_pinecone(all_records)
            
            if result:
                self.logger.info("Full content indexing completed successfully")
            else:
                self.logger.error("Full content indexing failed")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error during full content indexing: {str(e)}")
            return False