function onPumpClick(e){
	
	// Define pumping time in seconds
	let PUMPINGTIME = 3;

	// Call python function
	$.ajax({
	  url: '/turnWaterPumpOn/'+PUMPINGTIME,
	  type: 'get',
	  dataType: 'json',
	  success: function(response) {
		console.log(response);
		
		document.getElementById('time').innerHTML = response['time'];
		document.getElementById('temperature').innerHTML = response['temperature'];
		document.getElementById('humidity').innerHTML = response['humidity'];
		document.getElementById('light').innerHTML = response['light'];
	  },
	  error: function(xhr) {
	  }
	});

	// Disable/Enable button
	let button = document.getElementById('btnPump');
	let previusText = button.innerHTML;
	$("#btnPump").removeClass("btn-primary").addClass("btn-secondary").prop('disabled', true);
				  
	let downloadTimer = setInterval(function(){
		if(PUMPINGTIME <= 0)
		{
			clearInterval(downloadTimer);
			button.innerHTML = previusText;
			$("#btnPump").removeClass("btn-secondary").addClass("btn-primary").prop('disabled', false);
		}		
		else
		   button.innerHTML = PUMPINGTIME + "s Pumping";
		
		PUMPINGTIME -= 1;
	 }, 1000);
}

function initCharts(){
	const ctx1 = document.getElementById('chartAll');
	const chartAll = new Chart(ctx1, {
		type: 'line',
		data: data,
		options: {
			responsive: true,
			scales: {
				xAxis: {
					display: false,
				}
			}
		}
	});
	
	
}
