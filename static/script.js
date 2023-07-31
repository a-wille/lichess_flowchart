$(document).ready(function () {
    $("#search-form").submit(function (event) {
        event.preventDefault();
        const studyId = $("#study-id").val().trim();
        if (studyId !== "") {
            $.ajax({
                url: "/get_study_chapters",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({ studyId: studyId }),
                success: function (data) {
                    const chapters = data.chapters;
                    let chapterListHTML = "<h2>Select the chapters to build the tree on. </h2><ul style='list-style: none'>";
                    for (const chapter of chapters) {
                        chapterListHTML += `<li><input type="checkbox" value=${chapter.id}>${chapter.name}</li>`;
                    }
                    chapterListHTML += "</ul><input type=\"submit\" value=\"Submit\">";
                    $("#selection-form").html(chapterListHTML);
                },
                error: function (xhr, status, error) {
                    alert("Error fetching study data: " + error);
                },
            });
        }
    });
    $("#selection-form").submit(function (event) {
        event.preventDefault();
         // Get the selected items
        const selectedItems = [];
        const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            selectedItems.push(checkbox.value);
        });

        // You can process the selectedItems array here or send it to the server via a POST request.
        console.log('Selected Items:', selectedItems);
        const studyId = $("#study-id").val().trim();
        if (studyId !== "") {
            $.ajax({
                url: "/create_flowchart",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({ studyId: studyId, chapters: selectedItems}),
                success: function (data) {
                    document.getElementById("python").innerText = data['tree']
                    console.log(data)
                },
                error: function (xhr, status, error) {
                    alert("Error fetching study data: " + error);
                },
            });
        }
    });
});
