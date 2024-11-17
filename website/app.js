document.addEventListener("DOMContentLoaded", () => {
  const searchBtn = document.getElementById("searchBtn");
  const searchQuery = document.getElementById("searchQuery");
  const resultList = document.getElementById("resultList");
  const topPapersDay = document.getElementById("topPapersDay");
  const topPapersAllTime = document.getElementById("topPapersAllTime");

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
        `;
        resultList.appendChild(li);
      });
    }
  };

  const renderLeaderboards = (papers, container) => {
    container.innerHTML = "";
    if (papers.length === 0) {
      container.innerHTML = "<li>No top papers available.</li>";
    } else {
      papers.forEach((paper) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <strong>${paper.title}</strong>
          <p><em>Citations:</em> ${paper.citation_num}</p>
          <p><em>Composite Score:</em> ${paper.composite_score}</p>
        `;
        container.appendChild(li);
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
      .then((response) => response.json())
      .then((data) => renderSearchResults(data))
      .catch((error) => {
        console.error("Error fetching search results:", error);
        resultList.innerHTML = "<li>Failed to fetch search results.</li>";
      });
  });

  const fetchLeaderboards = () => {
    fetch("/top-papers-day")
      .then((response) => response.json())
      .then((data) => renderLeaderboards(data, topPapersDay))
      .catch((error) => {
        console.error("Error fetching top papers of the day:", error);
        topPapersDay.innerHTML = "<li>Failed to fetch top papers of the day.</li>";
      });

    fetch("/top-papers-all-time")
      .then((response) => response.json())
      .then((data) => renderLeaderboards(data, topPapersAllTime))
      .catch((error) => {
        console.error("Error fetching top papers of all time:", error);
        topPapersAllTime.innerHTML = "<li>Failed to fetch top papers of all time.</li>";
      });
  };

  fetchLeaderboards();
});
