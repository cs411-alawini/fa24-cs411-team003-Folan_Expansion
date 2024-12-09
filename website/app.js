document.addEventListener("DOMContentLoaded", () => {
  const searchBtn = document.getElementById("searchBtn");
  const searchQuery = document.getElementById("searchQuery");
  const resultList = document.getElementById("resultList");
  // const topPapersDay = document.getElementById("topPapersDay");
  // const topPapersAllTime = document.getElementById("topPapersAllTime");

  // Update navigation menu
  /*
  const header = document.querySelector('header');
  header.innerHTML += `
    <nav>
      <a href="profile.html">Profile</a> | <a href="/logout">Logout</a>
    </nav>
  `;
  */

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

      // Add event listeners to 'Like'/'Unlike' buttons
      document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', function() {
          const paperId = this.dataset.paperId;
          const action = this.textContent.trim().toLowerCase(); // Trim action text

          fetch(`/${action}`, { // Ensure no leading spaces
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId })
          })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              // Update button text
              this.textContent = action === 'like' ? 'Unlike' : 'Like';
            } else {
              alert(`Error: ${data.error}`);
            }
          })
          .catch(error => console.error('Error:', error));
        });
      });
    }
  };

  searchBtn.addEventListener("click", () => {
    const query = searchQuery.value.trim();
    if (!query) {
      alert("Please enter a search query.");
      return;
    }

    const keywords = query.split(",").map((kw) => kw.trim()).filter(Boolean);
    if (keywords.length < 1) {
      alert("Need at least one keyword.");
      return;
    }
    if (keywords.length > 3) {
      alert("At most three keywords allowed.");
      return;
    }

    fetch(`/search?keywords=${encodeURIComponent(keywords.join(","))}`)
      .then((response) => {
        if (response.status === 401) {
          // Not authenticated, redirect to login page
          window.location.href = 'login.html';
          return;
        }
        return response.json();
      })
      .then((data) => {
        if (data) {
          renderSearchResults(data);
        }
      })
      .catch((error) => {
        console.error("Error fetching search results:", error);
        resultList.innerHTML = "<li>Failed to fetch search results.</li>";
      });
  });

  // Remove fetchLeaderboards and its invocation
  /*  const fetchLeaderboards = () => {    fetch("/top-papers-day")      .then((response) => response.json())      .then((data) => renderLeaderboards(data, topPapersDay))      .catch((error) => {        console.error("Error fetching top papers of the day:", error);        topPapersDay.innerHTML = "<li>Failed to fetch top papers of the day.</li>";      });    fetch("/top-papers-all-time")      .then((response) => response.json())      .then((data) => renderLeaderboards(data, topPapersAllTime))      .catch((error) => {        console.error("Error fetching top papers of all time:", error);        topPapersAllTime.innerHTML = "<li>Failed to fetch top papers of all time.</li>";      });  };  fetchLeaderboards();  */});