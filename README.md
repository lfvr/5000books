**5000 Books**

A book review website for 5000 books, which pulls information from Goodreads and Google Books APIs. It also allows registered users to submit reviews to the site, which are displayed in full on each book page. 

The API for this site is accessible at /api/\<isbn>, which provides a JSON repsonse in the following format:<br/>
  {<br/>
    "title": "Book Title",<br/>
    "author": "Book Author",<br/>
    "year": 2020,<br/>
    "isbn": "1234567890",<br/>
    "review_count": 28,<br/>
    "average_score": 5.0<br/>
}<br/>
  
 Where review_count is the number of reviews for the book on the 5000 books website, and average_score is the average of those reviews.
