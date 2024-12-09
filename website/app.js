document.addEventListener("DOMContentLoaded", () => {
  const searchBtn = document.getElementById("searchBtn");
  const searchQuery = document.getElementById("searchQuery");
  const resultList = document.getElementById("resultList");
  const mostLikedBtn = document.getElementById("mostLikedBtn");
  const mostLikedList = document.getElementById("mostLikedList");
  const recommendBtn = document.getElementById("recommendBtn");
  const recommendList = document.getElementById("recommendList");
  const createLeaderboardBtn = document.getElementById("createLeaderboard"); // Added
  const leaderboardResults = document.getElementById("leaderboardResults"); // Added


  // Function to render search results
  const renderSearchResults = (results) => {
    resultList.innerHTML = "";
    if (results.length === 0) {
      resultList.innerHTML = "<li>No results found.</li>";
    } else {
      results.forEach((result) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <strong>${result.title}</strong> 
          <p>${result.abstract}</p>
          <p><em>Citations:</em> ${result.citation_num}</p>
          <p><em>Relevance Score:</em> ${result.relevance_score}</p>
          <p><em>Composite Score:</em> ${result.composite_score}</p>
          <button class="like-btn" data-paper-id="${result.paper_id}">
            ${result.liked ? 'Unlike' : 'Like'}
          </button>
        `;
        resultList.appendChild(li);
      });
      attachLikeButtonListeners();
    }
  };

  // Function to render most liked papers
  const renderMostLikedPapers = (results) => {
    mostLikedList.innerHTML = "";
    if (results.length === 0) {
      mostLikedList.innerHTML = "<li>No results found.</li>";
    } else {
      results.forEach((result) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <strong>${result.title}</strong> 
          <p><em>Total Likes:</em> ${result.total_likes}</p>
        `;
        mostLikedList.appendChild(li);
      });
    }
  };

  // Function to render recommendations
  const renderRecommendations = (results) => {
    recommendList.innerHTML = "";
    if (results.length === 0) {
      recommendList.innerHTML = "<li>No recommendations available.</li>";
    } else {
      results.forEach((result) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <strong>${result.title}</strong>
          <p>${result.abstract}</p>
          <p><em>Journal:</em> ${result.journal_name}</p>
          <p><em>Citations:</em> ${result.citation_num}</p>
          <p><em>Like Count:</em> ${result.like_count}</p>
          <button class="like-btn" data-paper-id="${result.paper_id}">
            Like
          </button>
        `;
        recommendList.appendChild(li);
      });
      attachLikeButtonListeners();
    }
  };

  // Attach 'Like' button event listeners
  const attachLikeButtonListeners = () => {
    document.querySelectorAll('.like-btn').forEach(button => {
      button.addEventListener('click', function () {
        const paperId = this.dataset.paperId;
        const action = this.textContent.trim().toLowerCase();

        fetch(`/${action}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paper_id: paperId })
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              this.textContent = action === 'like' ? 'Unlike' : 'Like';
            } else {
              alert(`Error: ${data.error}`);
            }
          })
          .catch(error => console.error('Error:', error));
      });
    });
  };

  // Event listeners for buttons
  searchBtn.addEventListener("click", () => {
    const query = searchQuery.value.trim();
    if (!query) {
      alert("Please enter a search query.");
      return;
    }

    const keywords = query.split(",").map((kw) => kw.trim()).filter(Boolean);
    if (keywords.length < 1 || keywords.length > 3) {
      alert("Enter 1-3 keywords.");
      return;
    }

    fetch(`/search?keywords=${encodeURIComponent(keywords.join(","))}`)
      .then(response => {
        if (response.status === 401) {
          window.location.href = 'login.html';
          return;
        }
        return response.json();
      })
      .then(data => data && renderSearchResults(data))
      .catch(error => {
        console.error("Error fetching search results:", error);
        resultList.innerHTML = "<li>Failed to fetch search results.</li>";
      });
  });

  mostLikedBtn.addEventListener("click", () => {
    fetch(`/most-liked-paper`)
      .then(response => {
        if (response.status === 401) {
          window.location.href = 'login.html';
          return;
        }
        return response.json();
      })
      .then(data => data && renderMostLikedPapers(data))
      .catch(error => {
        console.error("Error fetching most-liked papers:", error);
        mostLikedList.innerHTML = "<li>Failed to fetch most-liked papers.</li>";
      });
  });

  recommendBtn.addEventListener("click", () => {
    fetch("/recommend")
      .then(response => {
        if (response.status === 401) {
          window.location.href = "login.html";
          return;
        }
        return response.json();
      })
      .then(data => data && renderRecommendations(data))
      .catch(error => {
        console.error("Error fetching recommendations:", error);
        recommendList.innerHTML = "<li>Failed to fetch recommendations.</li>";
      });
  });

  createLeaderboardBtn.addEventListener("click", () => {
    fetch('/create-leaderboard', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      if (response.status === 401) {
        alert("You need to log in to create a leaderboard.");
        window.location.href = 'login.html';
        return;
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        alert("Error: " + data.error);
        return;
      }
  
      leaderboardResults.innerHTML = `<h3>Leaderboard</h3>`;
      const list = document.createElement('ul');
  
      data.top_papers.forEach(paper => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
          <strong>Ranking: ${paper.ranking}</strong>
          <p>Title: ${paper.title}</p>
          <p>Number of Likes: ${paper.num_likes}</p>
        `;
        list.appendChild(listItem);
      });
  
      leaderboardResults.appendChild(list);
    })
    .catch(error => {
      console.error('Error:', error);
      alert("Failed to create leaderboard.");
    });
  });

});