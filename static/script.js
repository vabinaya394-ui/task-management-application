function filterTasks(status) {

    const tasks = document.querySelectorAll(".task");

    tasks.forEach(function(task) {

        const taskStatus = task.getAttribute("data-status");

        if (status === "all") {
            task.style.display = "block";
        }
        else if (status === "pending" && taskStatus === "Pending") {
            task.style.display = "block";
        }
        else if (status === "completed" && taskStatus === "Completed") {
            task.style.display = "block";
        }
        else {
            task.style.display = "none";
        }

    });
}