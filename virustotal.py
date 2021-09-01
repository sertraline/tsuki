import os.path
import asyncio
import aio_pika
import hashlib

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType

from src.logger import DebugLogging
from time import sleep


def worker(args):
    data, logger = args

    path, mime, chat, m_id = data
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--disable-setuid-sandbox")
    driver = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(),
                              chrome_options=chrome_options)
    driver.implicitly_wait(10)
    logger.debug('GET https://virustotal.com')
    driver.get('https://virustotal.com')

    logger.debug('Query selectors for upload form')
    btn = driver.execute_script(
        "return document.querySelector('home-view').shadowRoot."
        "querySelector('vt-ui-main-upload-form').shadowRoot."
        "querySelector('input')"
    )
    btn.send_keys(path)
    attempts = 10
    while attempts:
        try:
            if attempts == 10:
                sleep(5)
            else:
                sleep(15)
            logger.debug('Attempting to resolve scan result')
            result = driver.execute_script(
                "return document.querySelector('file-view').shadowRoot."
                "querySelector('vt-ui-main-generic-report').shadowRoot."
                "querySelector('vt-ui-detections-widget').shadowRoot."
                "querySelector('.positives').textContent"
            )
            break
        except:
            logger.debug('Resolve failed, trying to find confirmation button')
            try:
                check_btn = driver.execute_script(
                    "return document.querySelector('home-view').shadowRoot."
                    "querySelector('vt-ui-main-upload-form').shadowRoot."
                    "querySelector('#confirmUpload');"
                )
                logger.debug('Button found, click')
                check_btn.click()
                continue
            except:
                attempts -= 1
                continue

    driver.close()
    driver.quit()
    logger.debug('Return result: <%s>' % result)
    return result


async def push(result):
    connection = await aio_pika.connect_robust(
        "amqp://guest:guest@127.0.0.1/", loop=asyncio.get_event_loop()
    )
    async with connection:
        routing_key = "virustotal_results"

        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(body=result.encode()),
            routing_key=routing_key,
        )


async def queue_checker(logger):
    loop = asyncio.get_event_loop()
    while True:
        logger.debug('Virustotal: connected to RabbitMQ')
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1/", loop=loop
        )
        queue_name = "virustotal"

        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(queue_name, auto_delete=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        data = message.body.decode('utf-8').split('\n')
                        if not os.path.isfile(data[0]):
                            continue
                        logger.debug('Launch worker for %s' % data)
                        future = await loop.run_in_executor(None, worker, [data, logger])
                        sha256_hash = hashlib.sha256()
                        with open(data[0], "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        await push(sha256_hash.hexdigest()+'\n'+future+'\n'+'\n'.join(data))
        await asyncio.sleep(5)


async def main():
    size = 2
    logger = DebugLogging(True).logger
    for i in range(size):
        logger.debug('Create task %d' % i)
        asyncio.get_event_loop().create_task(queue_checker(logger))
    while True:
        await asyncio.sleep(10)


if __name__ == '__main__':
    asyncio.run(main())
