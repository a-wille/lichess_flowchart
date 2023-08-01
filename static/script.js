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
                    let chapterListHTML = "<h3>Select chapters for tree creation. </h3><ul style='list-style: none;'>";
                    for (const chapter of chapters) {
                        chapterListHTML += `<li style="text-align: left;"><input type="checkbox" value=${chapter.id}>${chapter.name}</li>`;
                    }
                    chapterListHTML += "</ul><input type=\"submit\" value=\"Submit\">";
                    $("#selection-form").html(chapterListHTML);
                    document.getElementById("python").innerText = " ";
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
        const studyId = $("#study-id").val().trim();
        if (studyId !== "") {
            alert("Please be patient, loading results may take a minute!")
            document.getElementById("python").innerHTML = "";
            $.ajax({
                url: "/create_flowchart",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({ studyId: studyId, chapters: selectedItems}),
                success: function (data) {
                    for (d in data['trees']) {
                        name = data['trees'][d]
                        ntext = name.replace(/_/g, ' ')
                        img_src = '/static/' + name + '.png'
                        document.getElementById("python").innerHTML += "<h2 >" + ntext + "</h2><img src=" + img_src + " style='max-width: 100%; height: auto;'><br>"

                    }
                },
                error: function (xhr, status, error) {
                    alert("Error fetching study data: " + error);
                },
            });
        }
    });
});

