document.addEventListener("DOMContentLoaded", function () {
  // Mã JavaScript của bạn ở đây
  var urlParams = new URLSearchParams(window.location.search);
  console.log(urlParams);

  // Define the list of input field IDs
  var inputFieldIDs = [
    "keyword",
    "selectField",
    "chooseType",
    "TenSach",
    "ChuDe",
    "TacGia",
    "STTKe",
    "NXB",
    "NamXB",
    "formControlSelect1",
    "formControlSelect2",
    "formControlSelect3",
    "keyword1",
    "keyword2",
    "keyword3",
    "conditionSelect1",
    "conditionSelect2",
    "conditionSelect3",
  ];

  // Loop through the input field IDs
  for (var i = 0; i < inputFieldIDs.length; i++) {
    var inputID = inputFieldIDs[i];
    var inputElement = document.getElementById(inputID);

    // Get the corresponding Query Parameter value
    var paramValue = urlParams.get(inputID);
    console.log(inputID, paramValue);

    // Check if the parameter value is not null and not empty
    if (paramValue !== null && paramValue !== "") {
      // Assign the parameter value to the input field
      inputElement.value = paramValue;
    }
  }

  // Tự động điều chỉnh dộ rộng của table
  $(document).ready(function () {
    $("#books-table").DataTable();
  });

  $(document).ready(function () {
    $("#users-table").DataTable();
  });

  $(document).ready(function () {
    $("#history-table").DataTable();
  });
  // Quay lại trang trước mà không load lại trang
  document.getElementById("go-back").addEventListener("click", function () {
    window.history.back();
  });
});
